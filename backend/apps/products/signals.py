from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import ProductVariantAttributeValue, _compute_attribute_hash

@receiver(post_save, sender=ProductVariantAttributeValue)
@receiver(post_delete, sender=ProductVariantAttributeValue)
def update_variant_attributes_hash(sender, instance, **kwargs):
    variant = instance.variant
    attr_ids = list(
        variant.attribute_values.values_list("attribute_value_id", flat=True)
    )
    new_hash = _compute_attribute_hash(attr_ids)
    
    if variant.attributes_hash != new_hash:
        variant.attributes_hash = new_hash
        variant.save(update_fields=["attributes_hash", "updated_at"])
