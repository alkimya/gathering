/**
 * Lightbox for documentation images
 * Click on any image to view it in fullscreen
 */
(function() {
    'use strict';

    // Create lightbox elements
    var overlay = document.createElement('div');
    overlay.className = 'lightbox-overlay';

    var closeBtn = document.createElement('span');
    closeBtn.className = 'lightbox-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.title = 'Close (Esc)';

    var lightboxImg = document.createElement('img');
    lightboxImg.alt = 'Enlarged view';

    var hint = document.createElement('div');
    hint.className = 'lightbox-hint';
    hint.textContent = 'Click anywhere or press Esc to close';

    overlay.appendChild(closeBtn);
    overlay.appendChild(lightboxImg);
    overlay.appendChild(hint);
    document.body.appendChild(overlay);

    // Close lightbox function
    function closeLightbox() {
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    // Open lightbox function
    function openLightbox(src, alt) {
        lightboxImg.src = src;
        lightboxImg.alt = alt || 'Enlarged view';
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    // Add click handlers to all content images
    document.addEventListener('DOMContentLoaded', function() {
        var images = document.querySelectorAll('.rst-content img');

        images.forEach(function(img) {
            // Skip tiny images (icons, etc.)
            if (img.naturalWidth < 100 || img.naturalHeight < 100) {
                img.style.cursor = 'default';
                return;
            }

            img.addEventListener('click', function(e) {
                e.preventDefault();
                openLightbox(this.src, this.alt);
            });
        });
    });

    // Close on overlay click
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay || e.target === closeBtn) {
            closeLightbox();
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && overlay.classList.contains('active')) {
            closeLightbox();
        }
    });
})();
