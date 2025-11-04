/**
 * GitWiki JavaScript Utilities
 *
 * Reusable utility functions for security and common operations.
 *
 * AIDEV-NOTE: xss-prevention; Client-side HTML escaping for XSS prevention
 * See SECURITY.md for usage guidelines and examples.
 */

/**
 * Escape HTML special characters to prevent XSS attacks.
 *
 * This function should be used whenever inserting user-provided content
 * into HTML contexts (innerHTML, confirm dialogs, etc.).
 *
 * @param {string} text - The text to escape
 * @returns {string} - HTML-safe text with special characters escaped
 *
 * @example
 * // Prevent XSS in confirm dialogs
 * const userFileName = '"; alert("xss"); //';
 * const safe = escapeHtml(userFileName);
 * confirm(`Delete ${safe}?`); // Safe: Delete &quot;; alert(&quot;xss&quot;); //
 *
 * @example
 * // Prevent XSS when building HTML
 * const userInput = '<script>alert("xss")</script>';
 * const html = `<div>${escapeHtml(userInput)}</div>`;
 * // Result: <div>&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;</div>
 *
 * @example
 * // Attacks prevented:
 * escapeHtml('<img src=x onerror=alert(1)>')
 * // => '&lt;img src=x onerror=alert(1)&gt;'
 *
 * escapeHtml('\'><script>alert(document.cookie)</script>')
 * // => '&#x27;&gt;&lt;script&gt;alert(document.cookie)&lt;/script&gt;'
 */
function escapeHtml(text) {
    if (text == null) return '';

    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
    };

    return String(text).replace(/[&<>"'\/]/g, function(match) {
        return map[match];
    });
}

/**
 * Get CSRF token from cookies for Django requests.
 *
 * Extracted from Django documentation. Use this to get the CSRF token
 * for AJAX requests that modify data (POST, PUT, DELETE).
 *
 * @param {string} name - Cookie name (typically 'csrftoken')
 * @returns {string|null} - Cookie value or null if not found
 *
 * @example
 * // Use in fetch requests
 * fetch('/api/endpoint/', {
 *     method: 'POST',
 *     headers: {
 *         'X-CSRFToken': getCookie('csrftoken'),
 *         'Content-Type': 'application/json'
 *     },
 *     body: JSON.stringify(data)
 * });
 *
 * @example
 * // Use with FormData
 * const formData = new FormData();
 * formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Safely set text content in an element (no XSS risk).
 *
 * Helper function that uses textContent instead of innerHTML,
 * which is the safest way to insert user-provided text.
 *
 * @param {string|HTMLElement} elementOrSelector - Element or CSS selector
 * @param {string} text - Text to set
 *
 * @example
 * // Safe way to display user input
 * setText('#username', userProvidedName);
 *
 * // Equivalent to:
 * document.getElementById('username').textContent = userProvidedName;
 */
function setText(elementOrSelector, text) {
    const element = typeof elementOrSelector === 'string'
        ? document.querySelector(elementOrSelector)
        : elementOrSelector;

    if (element) {
        element.textContent = text;
    }
}
