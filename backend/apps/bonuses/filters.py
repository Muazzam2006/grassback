from django_filters import rest_framework as filters

from .models import Bonus, BonusType


class BonusFilter(filters.FilterSet):
    bonus_type = filters.ChoiceFilter(choices=BonusType.choices)
    level = filters.NumberFilter(field_name="level")
    created_at_after = filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_at_before = filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )

    class Meta:
        model = Bonus
        fields = ["bonus_type", "level", "status"]
