/*
 * Assumes graph_script.js eval'd beforehand
 *
 */

HIGHLIGHTS['rect'] = {'fill': 'red'};

$('.node, .edge').forEach(function(elem) {
    elem.addEventListener('click', function(event) {
        // TODO
    });
});

// Draw squares denoting factor and backbone matrices
$('.node, .edge').forEach(function(elem) {
    var type = elem.getAttribute('class');
    if (type == 'edge') {
        var match = elem.getAttribute('id').match(/`[^`]+`/g);
        // Don't draw sqares on Theta relations (Type→(same)Type)
        // and don't trigger click event
        if (match[0] == match[1]) {
            elem.removeEventListener('click', clickEventHandler);
            return;
        }
    }
    if (type == 'node') {
        var text = elem.querySelectorAll('ellipse + text')[0];
    } else if (type == 'edge') {
        var text = elem.querySelectorAll('text');
        text = text[text.length - 1];
    }
    var sizes = window.pybridge.graph_element_get_size(elem.id);
    for (var i=0; i<SIZES.length; ++i) {
        var size = SIZES[i],
            rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('width', size);
        rect.setAttribute('height', size);
        rect.setAttribute('fill', 'pink');
        rect.setAttribute('stroke', 'maroon');
        rect.setAttribute('rx', 2);  // Rounded corners
        if (type == 'node') {
            var x = 1*text.getAttribute('x') + text.clientWidth + 2,
                y = 1*text.getAttribute('y') + 2;
        } else if (type == 'edge') {
            var x = 1*text.getAttribute('x') + 5 + 2,
                y = 1*text.getAttribute('y') + 2;
        }
        rect.setAttribute('x', x + i*3);
        rect.setAttribute('y', y + i*2);
        elem.appendChild(rect);
    }
});
