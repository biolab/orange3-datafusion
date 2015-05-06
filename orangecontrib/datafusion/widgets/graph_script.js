
var svg = document.getElementsByTagName('svg')[0];

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
