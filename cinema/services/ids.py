from django.utils import timezone


def next_code(model, field_name, prefix, width=4):
    count = model.objects.count() + 1
    value = f"{prefix}{count:0{width}d}"
    while model.objects.filter(**{field_name: value}).exists():
        count += 1
        value = f"{prefix}{count:0{width}d}"
    return value


def next_order_number(order_model):
    year = timezone.localdate().year
    prefix = f"SS-{year}-"
    count = order_model.objects.filter(number__startswith=prefix).count() + 1
    number = f"{prefix}{count:04d}"
    while order_model.objects.filter(number=number).exists():
        count += 1
        number = f"{prefix}{count:04d}"
    return number
