param(
    [int]$MinLength = 6,
    [int]$FastGapMs = 80,
    [int]$FlushAfterMs = 150,
    [switch]$ShowRawKeys
)

$source = @"
using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;

public sealed class GlobalKeyboardMonitor : IDisposable
{
    private const int WH_KEYBOARD_LL = 13;
    private const int WM_KEYDOWN = 0x0100;
    private const int WM_SYSKEYDOWN = 0x0104;
    private const uint WM_QUIT = 0x0012;

    private readonly ConcurrentQueue<int> _queue = new ConcurrentQueue<int>();
    private readonly AutoResetEvent _queueEvent = new AutoResetEvent(false);
    private readonly NativeMethods.LowLevelKeyboardProc _hookProc;
    private Thread _messageThread;
    private IntPtr _hookHandle = IntPtr.Zero;
    private uint _threadId;
    private volatile bool _started;

    public GlobalKeyboardMonitor()
    {
        _hookProc = HookCallback;
    }

    public void Start()
    {
        if (_started)
        {
            return;
        }

        _messageThread = new Thread(MessageLoop);
        _messageThread.IsBackground = true;
        _messageThread.Name = "RFID Global Keyboard Monitor";
        _messageThread.Start();

        var startDeadline = DateTime.UtcNow.AddSeconds(5);
        while (!_started && DateTime.UtcNow < startDeadline)
        {
            Thread.Sleep(10);
        }

        if (!_started)
        {
            throw new InvalidOperationException("Nao foi possivel inicializar o hook global de teclado.");
        }
    }

    public int WaitForKey(int timeoutMs)
    {
        if (_queue.TryDequeue(out var key))
        {
            return key;
        }

        if (!_queueEvent.WaitOne(timeoutMs))
        {
            return -1;
        }

        return _queue.TryDequeue(out key) ? key : -1;
    }

    public void Stop()
    {
        if (!_started)
        {
            return;
        }

        NativeMethods.PostThreadMessage(_threadId, WM_QUIT, IntPtr.Zero, IntPtr.Zero);
        _messageThread.Join();
        _started = false;
    }

    public void Dispose()
    {
        Stop();
        _queueEvent.Dispose();
    }

    private void MessageLoop()
    {
        _threadId = NativeMethods.GetCurrentThreadId();

        using (var currentProcess = Process.GetCurrentProcess())
        using (var currentModule = currentProcess.MainModule)
        {
            var moduleHandle = NativeMethods.GetModuleHandle(currentModule.ModuleName);
            _hookHandle = NativeMethods.SetWindowsHookEx(WH_KEYBOARD_LL, _hookProc, moduleHandle, 0);
        }

        if (_hookHandle == IntPtr.Zero)
        {
            return;
        }

        _started = true;

        NativeMethods.MSG message;
        while (NativeMethods.GetMessage(out message, IntPtr.Zero, 0, 0) > 0)
        {
            NativeMethods.TranslateMessage(ref message);
            NativeMethods.DispatchMessage(ref message);
        }

        NativeMethods.UnhookWindowsHookEx(_hookHandle);
        _hookHandle = IntPtr.Zero;
    }

    private IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam)
    {
        if (nCode >= 0)
        {
            var message = wParam.ToInt32();
            if (message == WM_KEYDOWN || message == WM_SYSKEYDOWN)
            {
                var keyboardData = Marshal.PtrToStructure<NativeMethods.KBDLLHOOKSTRUCT>(lParam);
                _queue.Enqueue((int)keyboardData.vkCode);
                _queueEvent.Set();
            }
        }

        return NativeMethods.CallNextHookEx(_hookHandle, nCode, wParam, lParam);
    }

    private static class NativeMethods
    {
        public delegate IntPtr LowLevelKeyboardProc(int nCode, IntPtr wParam, IntPtr lParam);

        [StructLayout(LayoutKind.Sequential)]
        public struct KBDLLHOOKSTRUCT
        {
            public uint vkCode;
            public uint scanCode;
            public uint flags;
            public uint time;
            public UIntPtr dwExtraInfo;
        }

        [StructLayout(LayoutKind.Sequential)]
        public struct POINT
        {
            public int x;
            public int y;
        }

        [StructLayout(LayoutKind.Sequential)]
        public struct MSG
        {
            public IntPtr hwnd;
            public uint message;
            public UIntPtr wParam;
            public IntPtr lParam;
            public uint time;
            public POINT pt;
            public uint lPrivate;
        }

        [DllImport("user32.dll", SetLastError = true)]
        public static extern IntPtr SetWindowsHookEx(int idHook, LowLevelKeyboardProc lpfn, IntPtr hmod, uint dwThreadId);

        [DllImport("user32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool UnhookWindowsHookEx(IntPtr hhk);

        [DllImport("user32.dll", SetLastError = true)]
        public static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);

        [DllImport("user32.dll")]
        public static extern sbyte GetMessage(out MSG lpMsg, IntPtr hWnd, uint wMsgFilterMin, uint wMsgFilterMax);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool TranslateMessage([In] ref MSG lpMsg);

        [DllImport("user32.dll")]
        public static extern IntPtr DispatchMessage([In] ref MSG lpMsg);

        [DllImport("user32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool PostThreadMessage(uint idThread, uint Msg, IntPtr wParam, IntPtr lParam);

        [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        public static extern IntPtr GetModuleHandle(string lpModuleName);

        [DllImport("kernel32.dll")]
        public static extern uint GetCurrentThreadId();
    }
}
"@

if (-not ("GlobalKeyboardMonitor" -as [type])) {
    Add-Type -TypeDefinition $source -Language CSharp
}

$buffer = New-Object System.Text.StringBuilder
$lastPrintableAt = $null
$scanStartedAt = $null

function Reset-ScanBuffer {
    param([System.Text.StringBuilder]$ScanBuffer)

    $ScanBuffer.Clear() | Out-Null
    $script:lastPrintableAt = $null
    $script:scanStartedAt = $null
}

function Emit-Scan {
    param(
        [System.Text.StringBuilder]$ScanBuffer,
        [int]$MinimumLength
    )

    $value = $ScanBuffer.ToString()
    if ([string]::IsNullOrWhiteSpace($value)) {
        Reset-ScanBuffer -ScanBuffer $ScanBuffer
        return
    }

    if ($value.Length -lt $MinimumLength) {
        Write-Host ("[ignorado] Entrada curta demais: '{0}'" -f $value) -ForegroundColor DarkYellow
        Reset-ScanBuffer -ScanBuffer $ScanBuffer
        return
    }

    $durationMs = 0
    if ($script:scanStartedAt -and $script:lastPrintableAt) {
        $durationMs = [math]::Round((New-TimeSpan -Start $script:scanStartedAt -End $script:lastPrintableAt).TotalMilliseconds)
    }

    Write-Host ("[{0}] RFID={1} tamanho={2} duracao={3}ms" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $value, $value.Length, $durationMs) -ForegroundColor Green
    Reset-ScanBuffer -ScanBuffer $ScanBuffer
}

function Convert-VkToToken {
    param([int]$VirtualKey)

    switch ($VirtualKey) {
        { $_ -ge 0x30 -and $_ -le 0x39 } { return [char]$VirtualKey }
        { $_ -ge 0x41 -and $_ -le 0x5A } { return [char]$VirtualKey }
        { $_ -ge 0x60 -and $_ -le 0x69 } { return [char](48 + ($VirtualKey - 0x60)) }
        0x6A { return '*' }
        0x6D { return '-' }
        0x6E { return '.' }
        0x08 { return '<BACKSPACE>' }
        0x09 { return '<TAB>' }
        0x0D { return '<ENTER>' }
        0x1B { return '<ESC>' }
        default { return $null }
    }
}

Write-Host "Aguardando leituras do leitor RFID em modo teclado HID..." -ForegroundColor Cyan
Write-Host "O foco do terminal nao e necessario nesta versao." -ForegroundColor Cyan
Write-Host "Passe o cartao. ESC encerra. O script fecha a leitura por Enter/Tab ou por pausa curta entre teclas." -ForegroundColor DarkCyan
Write-Host "Evite digitar em outros aplicativos enquanto estiver testando." -ForegroundColor DarkCyan
Write-Host ""

$monitor = $null

try {
    $monitor = [GlobalKeyboardMonitor]::new()
    $monitor.Start()

    while ($true) {
        $vk = $monitor.WaitForKey(25)
        $now = Get-Date

        if ($vk -lt 0) {
            if ($buffer.Length -gt 0 -and $lastPrintableAt) {
                $idleMs = (New-TimeSpan -Start $lastPrintableAt -End $now).TotalMilliseconds
                if ($idleMs -ge $FlushAfterMs) {
                    Emit-Scan -ScanBuffer $buffer -MinimumLength $MinLength
                }
            }

            continue
        }

        $token = Convert-VkToToken -VirtualKey $vk

        if ($ShowRawKeys) {
            $displayToken = if ($null -ne $token) { $token } else { '<nao-mapeado>' }
            Write-Host ("[raw] vk=0x{0} token={1}" -f $vk.ToString('X2'), $displayToken) -ForegroundColor DarkGray
        }

        if ($token -eq '<ESC>') {
            break
        }

        if ($null -eq $token) {
            continue
        }

        if ($token -eq '<BACKSPACE>') {
            if ($buffer.Length -gt 0) {
                $buffer.Length = $buffer.Length - 1
            }
            continue
        }

        if ($token -in @('<ENTER>', '<TAB>')) {
            Emit-Scan -ScanBuffer $buffer -MinimumLength $MinLength
            continue
        }

        if ($lastPrintableAt -and $buffer.Length -gt 0) {
            $gapMs = (New-TimeSpan -Start $lastPrintableAt -End $now).TotalMilliseconds
            if ($gapMs -gt $FastGapMs) {
                Reset-ScanBuffer -ScanBuffer $buffer
            }
        }

        if (-not $scanStartedAt) {
            $scanStartedAt = $now
        }

        [void]$buffer.Append($token)
        $lastPrintableAt = $now
    }
}
finally {
    if ($monitor) {
        $monitor.Dispose()
    }

    Write-Host ""
    Write-Host "Monitor encerrado." -ForegroundColor Cyan
}