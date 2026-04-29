# applyStaticTranslations

- Nome da funcao: `applyStaticTranslations`
- Arquivo gerado: `applyStaticTranslations.md`
- Origem: `sistema/app/static/transport/app.js:1359`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: estatica translations
- Categoria: i18n + UI + state + date/time
- Responsabilidade: Aplica todas as traducoes estaticas do dashboard nos titulos, labels, botoes, atributos de acessibilidade e textos auxiliares presentes na pagina.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getActiveLanguageCode`, `getRequestTitle`, `getRouteKindLabel`, `mapScopeTitle`, `mapVehicleTypeLabel`, `refreshDatePanelLabels`, `syncVehicleModalFields`, `t`, `vehicleForm`, `vehicleModal`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function applyStaticTranslations() {
      if (typeof document === "undefined") {
        return;
      }

      document.documentElement.lang = getActiveLanguageCode();
      document.title = t("document.title");

      const brandKicker = document.querySelector(".transport-topbar-brand .transport-topbar-kicker");
      const brandTitle = document.querySelector(".transport-topbar-brand .transport-topbar-title");
      const supportKicker = document.querySelector(".transport-topbar-support .transport-topbar-kicker");
      const authLabels = document.querySelectorAll(".transport-auth-label");
      const requestSectionTitles = document.querySelectorAll(".transport-request-section .transport-section-title-link");
      const paneLinks = document.querySelectorAll(".transport-pane-title-link");
      const addVehicleButtons = document.querySelectorAll("[data-open-vehicle-modal]");
      const modalFieldLabels = vehicleForm ? vehicleForm.querySelectorAll(".transport-field > span") : [];
      const weekendLabels = weekendPersistenceFields.map(function (fieldElement) {
        return fieldElement.querySelector("span");
      });
      const regularLabels = regularPersistenceFields.map(function (fieldElement) {
        return fieldElement.querySelector("span");
      });
      const modalActionButtons = vehicleForm ? vehicleForm.querySelectorAll(".transport-modal-actions button") : [];
      const typeOptions = vehicleForm && vehicleForm.elements.tipo ? Array.from(vehicleForm.elements.tipo.options) : [];
      const routeOptions = vehicleForm && vehicleForm.elements.route_kind ? Array.from(vehicleForm.elements.route_kind.options) : [];

      if (brandKicker) {
        brandKicker.textContent = t("topbar.brand");
      }
      if (brandTitle) {
        brandTitle.textContent = t("topbar.allocationBoard");
      }
      if (supportKicker) {
        supportKicker.textContent = t("topbar.systemSupport");
      }
      if (routeTimeLabel) {
        routeTimeLabel.textContent = t("settings.workToHomeTime");
      }
      if (authLabels[0]) {
        authLabels[0].textContent = t("auth.key");
      }
      if (authLabels[1]) {
        authLabels[1].textContent = t("auth.pass");
      }

      const projectListTitle = document.querySelector("[data-project-list-toggle]");
      const userListTitle = document.querySelector("[data-user-list-title]");
      if (projectListTitle) {
        projectListTitle.textContent = t("panes.projectList");
      }
      if (userListTitle) {
        userListTitle.textContent = t("panes.userList");
      }
      if (requestSectionTitles[0]) {
        requestSectionTitles[0].textContent = getRequestTitle("extra");
      }
      if (requestSectionTitles[1]) {
        requestSectionTitles[1].textContent = getRequestTitle("weekend");
      }
      if (requestSectionTitles[2]) {
        requestSectionTitles[2].textContent = getRequestTitle("regular");
      }
      if (paneLinks[0]) {
        paneLinks[0].textContent = t("vehicles.lists.extra");
      }
      if (paneLinks[1]) {
        paneLinks[1].textContent = t("vehicles.lists.weekend");
      }
      if (paneLinks[2]) {
        paneLinks[2].textContent = t("vehicles.lists.regular");
      }
      addVehicleButtons.forEach(function (buttonElement) {
        const scope = buttonElement.dataset.openVehicleModal;
        if (!scope) {
          return;
        }
        buttonElement.setAttribute("aria-label", t(`vehicles.addAria.${scope}`));
      });
      if (settingsTrigger) {
        settingsTrigger.textContent = t("settings.dashboardLink");
        settingsTrigger.setAttribute("aria-label", t("settings.openAria"));
      }

      if (modalScopeLabel) {
        modalScopeLabel.textContent = mapScopeTitle(vehicleModal && vehicleModal.dataset.scope ? vehicleModal.dataset.scope : "regular");
      }
      const modalTitle = document.getElementById("transport-vehicle-modal-title");
      if (modalTitle) {
        modalTitle.textContent = t("modal.title");
      }
      document.querySelectorAll("[data-close-vehicle-modal]").forEach(function (buttonElement) {
        if (buttonElement.classList.contains("transport-modal-close")) {
          buttonElement.setAttribute("aria-label", t("modal.closeVehicleAria"));
          return;
        }
        buttonElement.textContent = t("modal.actions.cancel");
      });
      if (modalFieldLabels[0]) {
        modalFieldLabels[0].textContent = t("modal.fields.type");
      }
      if (modalFieldLabels[1]) {
        modalFieldLabels[1].textContent = t("modal.fields.plate");
      }
      if (modalFieldLabels[2]) {
        modalFieldLabels[2].textContent = t("modal.fields.color");
      }
      if (modalFieldLabels[3]) {
        modalFieldLabels[3].textContent = t("modal.fields.places");
      }
      if (modalFieldLabels[4]) {
        modalFieldLabels[4].textContent = t("modal.fields.tolerance");
      }
      if (modalFieldLabels[5]) {
        modalFieldLabels[5].textContent = t("modal.fields.departureDate");
      }
      if (modalFieldLabels[6]) {
        modalFieldLabels[6].textContent = t("modal.fields.departureTime");
      }
      if (modalFieldLabels[7]) {
        modalFieldLabels[7].textContent = t("modal.fields.route");
      }
      if (typeOptions[0]) {
        typeOptions[0].text = t("modal.options.car");
      }
      if (typeOptions[1]) {
        typeOptions[1].text = t("modal.options.minivan");
      }
      if (typeOptions[2]) {
        typeOptions[2].text = t("modal.options.van");
      }
      if (typeOptions[3]) {
        typeOptions[3].text = t("modal.options.bus");
      }
      if (routeOptions[0]) {
        routeOptions[0].text = getRouteKindLabel("home_to_work");
      }
      if (routeOptions[1]) {
        routeOptions[1].text = getRouteKindLabel("work_to_home");
      }
      if (weekendLabels[0]) {
        weekendLabels[0].textContent = t("modal.fields.everySaturday");
      }
      if (weekendLabels[1]) {
        weekendLabels[1].textContent = t("modal.fields.everySunday");
      }
      if (regularLabels[0]) {
        regularLabels[0].textContent = t("modal.fields.everyMonday");
      }
      if (regularLabels[1]) {
        regularLabels[1].textContent = t("modal.fields.everyTuesday");
      }
      if (regularLabels[2]) {
        regularLabels[2].textContent = t("modal.fields.everyWednesday");
      }
      if (regularLabels[3]) {
        regularLabels[3].textContent = t("modal.fields.everyThursday");
      }
      if (regularLabels[4]) {
        regularLabels[4].textContent = t("modal.fields.everyFriday");
      }
      if (modalActionButtons[1]) {
        modalActionButtons[1].textContent = t("modal.actions.save");
      }

      const settingsTitle = document.getElementById("transport-settings-modal-title");
      if (settingsTitle) {
        settingsTitle.textContent = t("settings.title");
      }
      document.querySelectorAll("[data-close-settings-modal]").forEach(function (buttonElement) {
        if (buttonElement.classList.contains("transport-modal-close")) {
          buttonElement.setAttribute("aria-label", t("settings.closeAria"));
          return;
        }
        buttonElement.textContent = t("settings.close");
      });
      if (settingsPreferencesTitle) {
        settingsPreferencesTitle.textContent = t("settings.preferences");
      }
      if (settingsVehicleDefaultsTitle) {
        settingsVehicleDefaultsTitle.textContent = t("settings.vehicleDefaults");
      }
      if (settingsLanguageLabel) {
        settingsLanguageLabel.textContent = t("settings.languages");
      }
      if (settingsTimeLabel) {
        settingsTimeLabel.textContent = t("settings.workToHomeTime");
      }
      if (settingsLastUpdateLabel) {
        settingsLastUpdateLabel.textContent = t("settings.lastUpdateTime");
      }
      if (settingsTimeNote) {
        settingsTimeNote.textContent = t("settings.workToHomeNote");
      }
      if (settingsVehicleDefaultsNote) {
        settingsVehicleDefaultsNote.textContent = t("settings.vehicleDefaultsNote");
      }
      if (settingsDefaultToleranceLabel) {
        settingsDefaultToleranceLabel.textContent = t("settings.standardTolerance");
      }
      if (settingsDefaultSeatLabels.carro) {
        settingsDefaultSeatLabels.carro.textContent = t("settings.defaultPlacesLabel", {
          type: mapVehicleTypeLabel("carro"),
        });
      }
      if (settingsDefaultSeatLabels.minivan) {
        settingsDefaultSeatLabels.minivan.textContent = t("settings.defaultPlacesLabel", {
          type: mapVehicleTypeLabel("minivan"),
        });
      }
      if (settingsDefaultSeatLabels.van) {
        settingsDefaultSeatLabels.van.textContent = t("settings.defaultPlacesLabel", {
          type: mapVehicleTypeLabel("van"),
        });
      }
      if (settingsDefaultSeatLabels.onibus) {
        settingsDefaultSeatLabels.onibus.textContent = t("settings.defaultPlacesLabel", {
          type: mapVehicleTypeLabel("onibus"),
        });
      }
      if (settingsCloseButton) {
        settingsCloseButton.textContent = t("settings.close");
      }

      const transportLayout = document.getElementById("tela01");
      if (transportLayout) {
        transportLayout.setAttribute("aria-label", t("layout.transportLayout"));
      }
      if (transportTopbar) {
        transportTopbar.setAttribute("aria-label", t("layout.quickActions"));
      }
      const datePanel = document.querySelector("[data-date-panel]");
      if (datePanel) {
        datePanel.setAttribute("aria-label", t("layout.selectedServiceDate"));
      }
      const previousDateButton = document.querySelector('[data-date-shift="-1"]');
      if (previousDateButton) {
        previousDateButton.setAttribute("aria-label", t("layout.previousServiceDate"));
      }
      const nextDateButton = document.querySelector('[data-date-shift="1"]');
      if (nextDateButton) {
        nextDateButton.setAttribute("aria-label", t("layout.nextServiceDate"));
      }
      const dateLink = document.querySelector("[data-date-link]");
      if (dateLink) {
        dateLink.setAttribute("aria-label", t("layout.returnServiceDateToToday"));
      }
      const authArea = document.querySelector(".transport-topbar-auth");
      if (authArea) {
        authArea.setAttribute("aria-label", t("layout.transportAccessFields"));
      }
      if (requestUserButton) {
        requestUserButton.setAttribute("aria-label", t("layout.requestUserCreation"));
      }
      const layoutDividers = document.querySelectorAll("[data-resize]");
      if (layoutDividers[0]) {
        layoutDividers[0].setAttribute("aria-label", t("layout.resizeMenuMain"));
      }
      const mainPanels = document.getElementById("tela01principal");
      if (mainPanels) {
        mainPanels.setAttribute("aria-label", t("layout.transportMainPanels"));
      }
      const requestSections = document.querySelectorAll(".transport-request-section");
      if (requestSections[0]) {
        requestSections[0].setAttribute("aria-label", t("layout.extraCarRequests"));
      }
      if (requestSections[1]) {
        requestSections[1].setAttribute("aria-label", t("layout.weekendCarRequests"));
      }
      if (requestSections[2]) {
        requestSections[2].setAttribute("aria-label", t("layout.regularCarRequests"));
      }
      if (layoutDividers[1]) {
        layoutDividers[1].setAttribute("aria-label", t("layout.resizeColumns"));
      }
      const carPanels = document.getElementById("tela01main_dir");
      if (carPanels) {
        carPanels.setAttribute("aria-label", t("layout.transportCarPanels"));
      }
      if (layoutDividers[2]) {
        layoutDividers[2].setAttribute("aria-label", t("layout.resizeExtraWeekend"));
      }
      if (layoutDividers[3]) {
        layoutDividers[3].setAttribute("aria-label", t("layout.resizeWeekendRegular"));
      }
      const footer = document.querySelector(".transport-footer-status");
      if (footer) {
        footer.setAttribute("aria-label", t("layout.transportNotifications"));
      }

      refreshDatePanelLabels();
      syncVehicleModalFields(vehicleModal && vehicleModal.dataset.scope ? vehicleModal.dataset.scope : "regular");
    }
```
