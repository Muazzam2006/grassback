document.addEventListener('DOMContentLoaded', function () {
    const hasVariantsCheckbox = document.getElementById('id_has_variants');
    if (!hasVariantsCheckbox) return;

    function toggleInlines() {
        // Find all inlines. In Unfold, they usually have specific classes or IDs.
        // ProductImage model -> likely 'productimage_set-group' (or similar based on related_name)
        // ProductVariant model -> likely 'variants-group' or 'productvariant_set-group'

        // Let's find them by their heading text or known possible IDs as a fallback.
        const allInlines = document.querySelectorAll('.js-inline-admin-formset');

        let imagesGroup = document.getElementById('productimage_set-group') || document.getElementById('images-group');
        let variantsGroup = document.getElementById('productvariant_set-group') || document.getElementById('variants-group');

        // Fallback: If IDs don't match exactly, find by looking at the inner HTML for the model names
        if (!imagesGroup || !variantsGroup) {
            allInlines.forEach(inline => {
                const text = inline.textContent || inline.innerText;
                const id = inline.id || "";

                // Identify images inline
                if (id.includes('image') || text.includes('Product image') || text.includes('Изображения') || text.includes('Product Image')) {
                    imagesGroup = inline.closest('.js-inline-admin-formset') || inline;
                }

                // Identify variants inline
                if (id.includes('variant') || text.includes('Product variant') || text.includes('Варианты товара') || text.includes('Product Variant')) {
                    variantsGroup = inline.closest('.js-inline-admin-formset') || inline;
                }
            });
        }

        if (hasVariantsCheckbox.checked) {
            if (imagesGroup) {
                imagesGroup.style.display = 'none';
                window.dispatchEvent(new Event('resize'));
            }
            if (variantsGroup) {
                variantsGroup.style.display = 'block';
                window.dispatchEvent(new Event('resize'));
            }
        } else {
            if (imagesGroup) {
                imagesGroup.style.display = 'block';
                window.dispatchEvent(new Event('resize'));
            }
            if (variantsGroup) {
                variantsGroup.style.display = 'none';
                window.dispatchEvent(new Event('resize'));
            }
        }
    }

    // Run on load
    toggleInlines();

    // Run on change
    hasVariantsCheckbox.addEventListener('change', toggleInlines);
});
