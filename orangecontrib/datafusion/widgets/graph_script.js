
function $(selector) { return document.querySelectorAll(selector) }
// document.querySelectorAll returns a NodeList which is missing mapping methods
NodeList.prototype.forEach = Array.prototype.forEach;

var svg = $('svg')[0];
svg.style.cursor = 'default';
svg.style.webkitUserSelect = 'none';
svg.style.margin = 'auto';

// Handle mousewheel zooming
curZoom = 1;
function clip(val, minval, maxval){
    return Math.min(Math.max(val, minval), maxval);
}
function changeZoom(element, delta) {
    curZoom = clip(curZoom + delta, .5, 3);
    element.style.zoom = curZoom;
}
window.addEventListener('mousewheel', function(event) {
    // wheelDeltaY magic from https://developer.mozilla.org/en-US/docs/Web/Events/mousewheel
    var dy = event['deltaY'] / 20 || event['wheelDeltaY'] / 1200;
    dy = clip(dy, -.1, .1);
    if (event.webkitDirectionInvertedFromDevice)
        dy = -dy;  // Apple is inverted
    changeZoom(svg, dy);
});

// Remove graph tooltip
// See: http://graphviz.org/content/tooltip-madness
//      http://www.graphviz.org/mantisbt/view.php?id=1491
$('title').forEach(function(title) {
    title.parentNode.removeChild(title);
});


// Highlight nodes when clicked
var ELEMENTS = $('.node, .edge');
function clickEventHandler(event) {
    // Deselect all elements
    dehighlight(ELEMENTS);
    // Only (re)select thus clicked element
    highlightOne(event.currentTarget);
    try {
        // Send the selection via pybridge for further processing
        window.pybridge.graph_element_selected(event.currentTarget.id);
        // And this is it for now
        event.stopPropagation();
    } catch (err) {
        // Do something else elsewhere
    };
}
ELEMENTS.forEach(function(elem) {
    elem.addEventListener('click', clickEventHandler);
});
// Dehighlight all nodes when background clicked
window.addEventListener('click', function(event) {
    dehighlight(ELEMENTS);
    // Indicate empty selection via pybridge
    try { window.pybridge.graph_element_selected(''); } catch (err) {};
});
var HIGHLIGHTS = {
    /* tagName: { attribute: [highlightedValue, originalValue] } */
    // Node
    'ellipse': {
        'fill': 'orange'
    },
    // Edge line
    'path': {
        'stroke': 'maroon'
    },
    // Edge arrow-head
    'polygon': {
        'stroke': 'maroon',
        'fill': 'maroon'
    },
    // Edge text
    'text': {
        'fill': 'maroon',
        'font-weight': 'bold'
    }
};
function SUBELEMENTS(elem) {
    return elem.querySelectorAll(Object.keys(HIGHLIGHTS).toString())
}
function dehighlightOne(elem) {
    SUBELEMENTS(elem).forEach(function(elem) {
        var props = HIGHLIGHTS[elem.tagName];
        for (var attr in props) {
            if (!elem.hasAttribute('data-prev-' + attr)) continue;
            var value = elem.getAttribute('data-prev-' + attr);
            elem.removeAttribute('data-prev-' + attr);
            if (value)
                elem.setAttribute(attr, value);
            else
                elem.removeAttribute(attr);
        }
    });
}
function highlightOne(elem) {
    SUBELEMENTS(elem).forEach(function(elem) {
        var props = HIGHLIGHTS[elem.tagName];
        for (var attr in props) {
            if (elem.hasAttribute('data-prev-' + attr)) continue;
            // Backup previous value
            elem.setAttribute('data-prev-' + attr, elem.getAttribute(attr) || '');
            // Set new value
            elem.setAttribute(attr, props[attr]);
        }
    });
}
function highlight(selector) {
    var elements = typeof selector == 'string' ? $(selector) : selector;
    elements.forEach(function(elem) { highlightOne(elem); });
}
function dehighlight(selector) {
    var elements = typeof selector == 'string' ? $(selector) : selector;
    elements.forEach(function(elem) { dehighlightOne(elem); });
}
