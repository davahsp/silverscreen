from pathlib import Path

from django import forms
from django.forms.widgets import CheckboxInput


class ImageWidget(forms.ClearableFileInput):
    template_name = "cinema/widgets/image.html"

    def __init__(self, attrs=None):
        default_attrs = {"accept": "image/*"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["clear_checked"] = context["widget"]["attrs"].pop("checked", False)
        filename = ""
        image_url = ""
        if value:
            filename = Path(getattr(value, "name", str(value))).name
            try:
                image_url = value.url
            except ValueError:
                image_url = ""
        context["widget"]["filename"] = filename
        context["widget"]["image_url"] = image_url
        return context

    def value_from_datadict(self, data, files, name):
        clear_name = self.clear_checkbox_name(name)
        self.checked = clear_name in data
        if not self.is_required and CheckboxInput().value_from_datadict(data, files, clear_name):
            return False
        return forms.FileInput.value_from_datadict(self, data, files, name)
