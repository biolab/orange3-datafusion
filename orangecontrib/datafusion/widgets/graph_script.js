
function $(selector) { return document.querySelectorAll(selector) }
// document.querySelectorAll returns a NodeList which is missing mapping methods
NodeList.prototype.forEach = Array.prototype.forEach;

var svg = $('svg')[0];
svg.style.cursor = 'default';
svg.style.webkitUserSelect = 'none';

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
ELEMENTS.forEach(function(elem) {
    elem.addEventListener('click', function(event) {
        // Deselect all elements
        ELEMENTS.forEach(function(elem) {
            dehighlightOne(elem);
        });
        try {
            // Send the selection via pybridge for further processing
            window.pybridge.graph_element_selected(elem.id);
            // Only (re)select thus clicked element
            highlightOne(elem);
        } catch (err) {
            // Do something else elsewhere
        };
    });
});
var EDGE_COLORS = ['maroon', 'black'];
var HIGHLIGHTS = {
    /* tagName: { attribute: [highlightedValue, originalValue] } */
    // Node
    'ellipse': {
        'fill': ['orange', 'white']
    },
    // Edge line
    'path': {
        'stroke': EDGE_COLORS
    },
    // Edge arrow-head
    'polygon': {
        'stroke': EDGE_COLORS,
        'fill': EDGE_COLORS
    },
    // Edge text
    'text': {
        'fill': EDGE_COLORS,
        'font-weight': ['bold', 'normal']
    }
};
function SUBELEMENTS(elem) {
    return elem.querySelectorAll(Object.keys(HIGHLIGHTS).toString())
}
function dehighlightOne(elem) {
    SUBELEMENTS(elem).forEach(function(elem) {
        var props = HIGHLIGHTS[elem.tagName];
        for (var attr in props) {
            elem.setAttribute(attr, props[attr][1]);
        }
    });
}
function highlightOne(elem) {
    SUBELEMENTS(elem).forEach(function(elem) {
        var props = HIGHLIGHTS[elem.tagName];
        for (var attr in props) {
            elem.setAttribute(attr, props[attr][0]);
        }
    });
}
function highlight(selector) {
    $(selector).forEach(function(elem) {
        highlightOne(elem);
    });
}
