document.addEventListener("DOMContentLoaded", function () {
    const SELECTOR = 'select[data-grouped-attribute-picker="1"]';

    function hasSelect2() {
        return !!(
            window.django &&
            window.django.jQuery &&
            window.django.jQuery.fn &&
            window.django.jQuery.fn.select2
        );
    }

    function refreshSelect2(select, placeholder) {
        if (!hasSelect2()) {
            return;
        }

        const $ = window.django.jQuery;
        const $select = $(select);

        if ($select.hasClass("select2-hidden-accessible")) {
            $select.select2("destroy");
        }

        $select.select2({
            theme: "admin-autocomplete",
            width: "100%",
            placeholder: placeholder || "",
            allowClear: true,
            minimumResultsForSearch: 10,
        });
    }

    function parseRows(sourceSelect) {
        return Array.from(sourceSelect.options)
            .map((option) => ({
                id: option.value,
                attributeId: option.dataset.attributeId,
                attributeName: option.dataset.attributeName,
                valueName: option.dataset.valueName || option.textContent,
                option,
            }))
            .filter((row) => row.id && row.attributeId);
    }

    function buildAttributeMap(rows) {
        const byAttribute = new Map();
        rows.forEach((row) => {
            if (!byAttribute.has(row.attributeId)) {
                byAttribute.set(row.attributeId, {
                    id: row.attributeId,
                    name: row.attributeName,
                    values: [],
                });
            }
            byAttribute.get(row.attributeId).values.push(row);
        });

        return Array.from(byAttribute.values()).sort((a, b) =>
            a.name.localeCompare(b.name)
        );
    }

    function create(tag, className, text) {
        const node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (typeof text === "string") {
            node.textContent = text;
        }
        return node;
    }

    function styleAsPrimaryUnfoldButton(button) {
        const saveButton = document.querySelector('#submit-row button[name="_save"]');

        if (saveButton && saveButton.className) {
            button.className = saveButton.className + " grouped-attribute-picker__add";
            button.classList.remove("w-full");
            button.classList.remove("lg:w-auto");
            button.style.width = "auto";
            return;
        }

        button.className =
            "grouped-attribute-picker__add font-medium inline-flex group items-center gap-2 px-3 py-2 " +
            "relative rounded-default justify-center whitespace-nowrap cursor-pointer border border-base-200 " +
            "bg-primary-600 border-transparent text-white hover:bg-primary-600/80";
    }

    function initPicker(sourceSelect) {
        const sourceName = sourceSelect.getAttribute("name") || "";
        const sourceId = sourceSelect.id || "";

        if (
            sourceName.includes("__prefix__") ||
            sourceId.includes("__prefix__") ||
            sourceSelect.closest(".empty-form")
        ) {
            return;
        }

        if (sourceSelect.dataset.groupedAttributePickerInit === "1") {
            return;
        }

        const rows = parseRows(sourceSelect);
        const attributes = buildAttributeMap(rows);
        const byAttributeId = new Map(attributes.map((item) => [item.id, item]));
        const widgetLabel = sourceSelect.dataset.widgetLabel || "Характеристики";

        sourceSelect.dataset.groupedAttributePickerInit = "1";
        sourceSelect.style.display = "none";

        const root = create("div", "grouped-attribute-picker");
        const controls = create("div", "grouped-attribute-picker__controls");
        const attrWrap = create("div", "grouped-attribute-picker__field grouped-attribute-picker__field--attribute");
        const valueWrap = create("div", "grouped-attribute-picker__field grouped-attribute-picker__field--value");
        const attrSelect = create("select", "grouped-attribute-picker__native-select");
        const valueSelect = create("select", "grouped-attribute-picker__native-select");
        const addButton = create("button", "grouped-attribute-picker__add", "Добавить");
        const selectedList = create("div", "grouped-attribute-picker__selected");

        addButton.type = "button";
        styleAsPrimaryUnfoldButton(addButton);

        function selectedIds() {
            return new Set(rows.filter((row) => row.option.selected).map((row) => row.id));
        }

        function fillAttributeSelect() {
            attrSelect.innerHTML = "";

            const placeholder = create("option", "", "Выберите характеристику");
            placeholder.value = "";
            attrSelect.appendChild(placeholder);

            if (!attributes.length) {
                placeholder.textContent = "Сначала добавьте характеристики и их значения";
                attrSelect.disabled = true;
                valueSelect.disabled = true;
                addButton.disabled = true;
                refreshSelect2(attrSelect, "");
                refreshSelect2(valueSelect, "");
                return;
            }

            attributes.forEach((item) => {
                const option = create("option", "", item.name);
                option.value = item.id;
                attrSelect.appendChild(option);
            });

            attrSelect.disabled = false;
            valueSelect.disabled = false;
            addButton.disabled = false;
            refreshSelect2(attrSelect, "Выберите характеристику");
        }

        function fillValueSelect(attributeId) {
            valueSelect.innerHTML = "";

            const placeholder = create(
                "option",
                "",
                attributeId ? "Выберите значение" : "Сначала выберите характеристику"
            );
            placeholder.value = "";
            valueSelect.appendChild(placeholder);

            if (!attributeId || !byAttributeId.has(attributeId)) {
                refreshSelect2(valueSelect, "Сначала выберите характеристику");
                return;
            }

            const picked = selectedIds();
            byAttributeId
                .get(attributeId)
                .values.filter((row) => !picked.has(row.id))
                .forEach((row) => {
                    const option = create("option", "", row.valueName);
                    option.value = row.id;
                    valueSelect.appendChild(option);
                });

            refreshSelect2(valueSelect, "Выберите значение");
        }

        function renderSelected() {
            selectedList.innerHTML = "";

            if (!attributes.length) {
                const msg = create(
                    "div",
                    "grouped-attribute-picker__empty text-font-subtle-light dark:text-font-subtle-dark",
                    "Нет доступных значений. Сначала создайте характеристики и значения в разделе Tune > Характеристики."
                );
                const link = create(
                    "a",
                    "grouped-attribute-picker__link text-primary-600 dark:text-primary-500",
                    "Открыть характеристики"
                );
                link.href = "/admin/products/productattribute/";
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                selectedList.appendChild(msg);
                selectedList.appendChild(link);
                return;
            }

            const selectedRows = rows.filter((row) => row.option.selected);
            if (!selectedRows.length) {
                selectedList.appendChild(
                    create(
                        "div",
                        "grouped-attribute-picker__empty text-font-subtle-light dark:text-font-subtle-dark",
                        widgetLabel + ": ничего не выбрано"
                    )
                );
                return;
            }

            selectedRows.forEach((row) => {
                const item = create(
                    "div",
                    "grouped-attribute-picker__item bg-white border border-base-200 rounded-default px-3 py-2 flex items-center justify-between gap-2 dark:bg-base-900 dark:border-base-700"
                );
                const label = create(
                    "span",
                    "grouped-attribute-picker__item-label text-sm text-font-default-light dark:text-font-default-dark",
                    row.attributeName + ": " + row.valueName
                );
                const removeBtn = create(
                    "button",
                    "button grouped-attribute-picker__remove border border-base-200 rounded-default px-3 h-[32px] text-sm font-medium dark:border-base-700",
                    "Удалить"
                );

                removeBtn.type = "button";
                removeBtn.addEventListener("click", function () {
                    row.option.selected = false;
                    renderSelected();
                    fillValueSelect(attrSelect.value);
                });

                item.appendChild(label);
                item.appendChild(removeBtn);
                selectedList.appendChild(item);
            });
        }

        addButton.addEventListener("click", function () {
            const valueId = valueSelect.value;
            if (!valueId) {
                return;
            }

            const selectedRow = rows.find((row) => row.id === valueId);
            if (!selectedRow) {
                return;
            }

            selectedRow.option.selected = true;
            renderSelected();
            fillValueSelect(attrSelect.value);
        });

        attrSelect.addEventListener("change", function () {
            fillValueSelect(attrSelect.value);
        });

        if (hasSelect2()) {
            const $ = window.django.jQuery;
            $(attrSelect).on("select2:select select2:clear", function () {
                fillValueSelect(attrSelect.value);
            });
        }

        attrWrap.appendChild(attrSelect);
        valueWrap.appendChild(valueSelect);
        controls.appendChild(attrWrap);
        controls.appendChild(valueWrap);
        controls.appendChild(addButton);
        root.appendChild(controls);
        root.appendChild(selectedList);
        sourceSelect.insertAdjacentElement("beforebegin", root);

        fillAttributeSelect();
        fillValueSelect("");
        renderSelected();
    }

    function initAll() {
        document.querySelectorAll(SELECTOR).forEach(initPicker);
    }

    initAll();
    new MutationObserver(initAll).observe(document.body, { childList: true, subtree: true });
});
