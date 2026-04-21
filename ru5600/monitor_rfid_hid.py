from __future__ import annotations

import argparse
import queue
import sys
import time
from dataclasses import dataclass

import pywinusb.hid as hid


DEFAULT_VENDOR_ID = 0x1A86
DEFAULT_PRODUCT_ID = 0xE010


@dataclass
class DeviceSelection:
    index: int
    device: hid.HidDevice


def parse_int(value: str) -> int:
    return int(value, 0)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitora relatorios HID brutos de leitores RFID USB semelhantes ao RU5600."
    )
    parser.add_argument("--vendor-id", type=parse_int, default=DEFAULT_VENDOR_ID)
    parser.add_argument("--product-id", type=parse_int, default=DEFAULT_PRODUCT_ID)
    parser.add_argument("--index", type=int, default=0, help="Indice do dispositivo na lista encontrada.")
    parser.add_argument("--list-only", action="store_true", help="Lista os dispositivos encontrados e encerra.")
    return parser


def enumerate_devices(vendor_id: int, product_id: int) -> list[hid.HidDevice]:
    return hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id).get_devices()


def extract_interface_tag(device_path: str | None) -> str:
    if not device_path:
        return "desconhecida"

    lowered = device_path.lower()
    for part in lowered.split("#"):
        if part.startswith("mi_"):
            return part.upper()

        marker = "&mi_"
        if marker in part:
            return part[part.index(marker) + 1 : part.index(marker) + 6].upper()

    return "desconhecida"


def print_devices(devices: list[hid.HidDevice]) -> None:
    if not devices:
        print("Nenhum dispositivo HID correspondente foi encontrado.")
        return

    print("Dispositivos HID encontrados:")
    for index, device in enumerate(devices):
        print(
            f"[{index}] fabricante={device.vendor_name!r} produto={device.product_name!r} "
            f"interface={extract_interface_tag(getattr(device, 'device_path', None))}"
        )
        print(f"     path={device.device_path}")
        print(f"     instance_id={getattr(device, 'instance_id', '')}")


def choose_device(devices: list[hid.HidDevice], index: int) -> DeviceSelection:
    if not devices:
        raise RuntimeError("Nenhum dispositivo HID correspondente foi encontrado.")

    if index < 0 or index >= len(devices):
        raise RuntimeError(f"Indice invalido: {index}. Total encontrado: {len(devices)}")

    return DeviceSelection(index=index, device=devices[index])


def format_hex(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def printable_ascii_candidate(payload: bytes) -> str | None:
    chars = [chr(byte) for byte in payload if 32 <= byte <= 126]
    text = "".join(chars).strip()
    return text if len(text) >= 4 else None


def utf16le_ascii_candidate(payload: bytes) -> str | None:
    if len(payload) < 4 or len(payload) % 2 != 0:
        return None

    even_bytes = payload[0::2]
    odd_bytes = payload[1::2]
    if not odd_bytes or not all(byte == 0 for byte in odd_bytes):
        return None

    chars = [chr(byte) for byte in even_bytes if 32 <= byte <= 126]
    text = "".join(chars).strip()
    return text if len(text) >= 4 else None


def compact_payload(payload: bytes) -> bytes:
    return bytes(byte for byte in payload if byte not in (0x00, 0xFF))


def candidate_descriptions(payload: bytes) -> list[str]:
    compact = compact_payload(payload)
    candidates: list[str] = []

    ascii_candidate = printable_ascii_candidate(compact)
    if ascii_candidate:
        candidates.append(f"ASCII={ascii_candidate}")

    utf16_candidate = utf16le_ascii_candidate(payload.rstrip(b"\x00"))
    if utf16_candidate:
        candidates.append(f"UTF16LE={utf16_candidate}")

    if 4 <= len(compact) <= 16:
        candidates.append(f"HEX={compact.hex().upper()}")
        candidates.append(f"DEC_BE={int.from_bytes(compact, byteorder='big')}")
        candidates.append(f"DEC_LE={int.from_bytes(compact, byteorder='little')}")

    return unique_preserve_order(candidates)


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    devices = enumerate_devices(args.vendor_id, args.product_id)
    print_devices(devices)

    if args.list_only:
        return 0 if devices else 1

    selection = choose_device(devices, args.index)
    device = selection.device

    report_queue: queue.Queue[bytes] = queue.Queue()
    last_payload: bytes | None = None
    last_report_at = 0.0

    def raw_handler(raw_data: list[int]) -> None:
        report_queue.put(bytes(raw_data))

    device.open()
    device.set_raw_data_handler(raw_handler)

    try:
        caps = device.hid_caps
        usage_page = getattr(caps, "usage_page", None)
        usage = getattr(caps, "usage", None)
        print("")
        print(
            f"Escutando {device.product_name!r} no indice {selection.index} "
            f"(interface={extract_interface_tag(device.device_path)}, usage_page=0x{usage_page:04X}, usage={usage})."
        )
        print("Passe o cartao. Ctrl+C encerra.")
        print("")

        while True:
            try:
                report = report_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if not report:
                continue

            report_id = report[0]
            payload = report[1:]
            if not any(payload):
                continue

            now = time.monotonic()
            if payload == last_payload and (now - last_report_at) < 0.25:
                continue

            last_payload = payload
            last_report_at = now

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] report_id=0x{report_id:02X}")
            print(f"  raw_hex={format_hex(payload)}")

            candidates = candidate_descriptions(payload)
            if candidates:
                for candidate in candidates:
                    print(f"  candidato={candidate}")
            else:
                compact = compact_payload(payload)
                if compact:
                    print(f"  compact_hex={compact.hex().upper()}")
                else:
                    print("  sem candidato textual; veja raw_hex acima")

            print("")
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\nMonitor encerrado.")
        return 0
    finally:
        try:
            device.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())