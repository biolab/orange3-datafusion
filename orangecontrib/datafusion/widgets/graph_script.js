
$ = document.querySelectorAll.bind(document);
NodeList.prototype.forEach = Array.prototype.forEach;


var svg = $('svg')[0];

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
var elements = $('.node, .edge')
elements.forEach(function(elem) {
    elem.addEventListener('click', function(event) {
        elements.forEach(function(elem) {
            elem.classList.remove('selected');
        });
        elem.classList.add('selected');
        // Send the selection via pybridge for further processing
        window.pybridge.graph_element_selected(elem.id);
        //~ alert(window.pybridge);
    });
});
function highlight(selector) {
    $(selector).forEach(function(elem) {
        elem.classList.add('selected');
    });
}
