from django import forms
from django.forms.models import ModelChoiceIteratorValue

from .models import Product, ProductAttributeValue, ProductVariant, ProductVariantAttributeValue


class ProductAttributeValueGroupedWidget(forms.SelectMultiple):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if isinstance(value, ModelChoiceIteratorValue) and value.instance is not None:
            attr_id = str(value.instance.attribute_id)
            attr_name = value.instance.attribute.name
            value_name = value.instance.value
            option.setdefault("attrs", {})
            option["attrs"]["data-attribute-id"] = attr_id
            option["attrs"]["data-attribute-name"] = attr_name
            option["attrs"]["data-value-name"] = value_name
        return option


def _setup_grouped_attribute_field(field, widget_label: str):
    field.queryset = ProductAttributeValue.objects.select_related("attribute").order_by(
        "attribute__name", "value"
    )
    widget = ProductAttributeValueGroupedWidget(
        attrs={
            "data-grouped-attribute-picker": "1",
            "data-widget-label": widget_label,
        }
    )
    widget.choices = field.choices
    field.widget = widget


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "attribute_values" in self.fields:
            self.fields["attribute_values"].help_text = ""
            _setup_grouped_attribute_field(self.fields["attribute_values"], "Характеристики товара")


class ProductVariantAdminForm(forms.ModelForm):
    attribute_value_ids = forms.ModelMultipleChoiceField(
        queryset=ProductAttributeValue.objects.none(),
        required=False,
        label="Характеристики товара",
        help_text="Выберите значения характеристик для варианта товара.",
    )

    class Meta:
        model = ProductVariant
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "attribute_value_ids" in self.fields:
            _setup_grouped_attribute_field(self.fields["attribute_value_ids"], "Характеристики товара")
            if self.instance and self.instance.pk:
                self.fields["attribute_value_ids"].initial = list(
                    self.instance.attribute_values.values_list("attribute_value_id", flat=True)
                )

    def clean_attribute_value_ids(self):
        selected_values = self.cleaned_data.get("attribute_value_ids")
        if selected_values is None:
            return selected_values

        seen_attributes = set()
        for attr_value in selected_values:
            if attr_value.attribute_id in seen_attributes:
                raise forms.ValidationError(
                    "Нельзя выбрать два значения одной характеристики для варианта."
                )
            seen_attributes.add(attr_value.attribute_id)
        return selected_values

    def _save_m2m(self):
        super()._save_m2m()

        if not self.instance.pk:
            return

        selected_values = self.cleaned_data.get("attribute_value_ids")
        if selected_values is None:
            return

        ProductVariantAttributeValue.objects.filter(variant=self.instance).delete()
        ProductVariantAttributeValue.objects.bulk_create(
            [
                ProductVariantAttributeValue(variant=self.instance, attribute_value=value)
                for value in selected_values
            ]
        )
