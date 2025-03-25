document.addEventListener('DOMContentLoaded', function() {
    // Improved selective blur effect on scroll
    const container = document.querySelector('.container');
    const glassPanel = document.querySelector('.glass-panel');

    if (container && glassPanel) {
        window.addEventListener('scroll', function() {
            // Get the scroll position
            const scrollY = window.scrollY;
            const containerTop = container.offsetTop;
            const containerHeight = container.offsetHeight;
            const glassTop = glassPanel.offsetTop;
            const glassHeight = glassPanel.offsetHeight;

            // Only blur content that's out of view
            if (scrollY > 50) {
                const sections = document.querySelectorAll('.glass-panel > div');
                sections.forEach(function(section) {
                    const sectionTop = section.offsetTop + glassTop;
                    const sectionHeight = section.offsetHeight;

                    // If the section is out of viewport, add blur
                    if (scrollY > sectionTop + sectionHeight || 
                        scrollY + window.innerHeight < sectionTop) {
                        section.classList.add('blur-out');
                    } else {
                        section.classList.remove('blur-out');
                    }
                });
            } else {
                // Remove all blurs when at the top
                const blurred = document.querySelectorAll('.blur-out');
                blurred.forEach(function(el) {
                    el.classList.remove('blur-out');
                });
            }
        });
    }

    // Hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    if (alerts.length > 0) {
        setTimeout(function() {
            alerts.forEach(function(alert) {
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.5s ease';
                setTimeout(function() {
                    alert.remove();
                }, 500);
            });
        }, 5000);
    }

    // Copyable text functionality
    const copyButtons = document.querySelectorAll('.copy-button');
    if (copyButtons) {
        copyButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                const textToCopy = this.getAttribute('data-copy-target');
                const textElement = document.querySelector(textToCopy);
                
                if (textElement) {
                    const textValue = textElement.innerText;
                    navigator.clipboard.writeText(textValue).then(function() {
                        alert('Copied to clipboard!');
                    }).catch(function(err) {
                        console.error('Could not copy text: ', err);
                    });
                }
            });
        });
    }

    // FAQ accordion functionality if on FAQ page
    const faqItems = document.querySelectorAll('.faq-item');
    if (faqItems) {
        faqItems.forEach(function(item) {
            const question = item.querySelector('.faq-question');
            if (question) {
                question.addEventListener('click', function() {
                    item.classList.toggle('active');
                    const icon = question.querySelector('i');
                    if (icon) {
                        if (item.classList.contains('active')) {
                            icon.className = 'fas fa-chevron-up';
                        } else {
                            icon.className = 'fas fa-chevron-down';
                        }
                    }
                });
            }
        });
    }
});

// Functions for the humanize page
function copyToClipboard() {
    const text = document.querySelector('.humanized-text').innerText;
    navigator.clipboard.writeText(text).then(() => {
        alert('Text copied to clipboard!');
    });
}

function downloadText() {
    const text = document.querySelector('.humanized-text').innerText;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'humanized_text.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
