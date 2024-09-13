

function decorateNodeListMXML(nodeList, name) {
    /**
     * Decorates a list of nodes with a given fixed name and an increasing id number.
     * @param {Object[]} nodeList An array containing a list of nodes.
     * @param {string} name A base name to provide to each node.
     */
    nodeList.forEach((node, index) => {
        node.id = `${name}${index + 1}`;
    });
}

function findAndDecorateMXML(root, name, ...xpath) {
    /**
     * Finds all elements found within a set of xpath queries in measures and identifies them with name.
     * @param {Object} root The base score-partwise element of MusicXML in the DOM.
     * @param {string} name A base name to provide to each node.
     * @param {string[]} ...xpath An array containing a list of xpaths under measure to check.
     */
    decorateNodeListMXML(findMultipleMXML(root, ...xpath), name);
}

function findMXML(root, xpath) {
    let output = [];
    let query = document.evaluate("./part/measure/".concat(xpath), root, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    for (let ii = 0, length = query.snapshotLength; ii < length; ii++) {
        output.push(query.snapshotItem(ii));
    }
    return output;
}

function findMultipleMXML(root, ...xpath) {
    let children = [];

    for (let ii = 0; ii < xpath.length; ii++) {
        let path_spec = xpath[ii];
        let subchildren = findMXML(root, path_spec);
        children.concat(subchildren);
        console.log("Children from ", path_spec, " xpath query: ", subchildren);
        
    };
    return children;
}


function decorateNotesMXML(root) {
    /**
     * Decorates notes and rests with MXML ids.
     * @param {Object} root Root DOM object containing all MusicXML elements.
     */
    let allNodes = root.querySelectorAll('note');

    let noteNodes = Array.from(allNodes).filter(node => {
        let child = node.querySelector('rest');
        return !child || !child.contains(child);
    });

    let restNodes = Array.from(allNodes).filter(node => {
        return node.querySelector("rest")
    });

    decorateNodeListMXML(noteNodes, "note");
    decorateNodeListMXML(restNodes, "rest");
}

function decorateBeamsMXML(root) {
    let beamElements = findMXML(root, "note/beam");
    let startBeams = beamElements.filter(beam => {
        switch (beam.innerText) {
        case "begin":
        case "backward hook":
        case "forward hook":
            return true
            break;
        default:
            return false;
            break;
        }
    });
    console.log("Found beams: ", startBeams);
    decorateNodeListMXML(startBeams, "beam");
}

function findAndDecorateEndToEndMXML(root, name, ...xpath) {
    let elements = findMultipleMXML(root, ...xpath);

    // Initialize idents object with the last segment of each path
    let idents = {};
    xpath.forEach(path => {
        let key = path.split("/").pop();
        idents[key] = 1;
    });

    elements.forEach(element => {
        let style = element.getAttribute("type");
        let tag = element.tagName;

        if (!style) {
            throw new Error("End to end object without style property");
        }

        if (["start", "crescendo", "diminuendo", "let-ring", "up", "down", "sostenuto"].includes(style)) {
            element.setAttribute("id", `${tag}${idents[tag]}`);
            idents[tag]++;
        }
    });  
}

function decorateMeasures(root) {
    let parts = root.querySelectorAll("part");
    parts.forEach(part => {
        let partId = part.id;
        Array.from(part.children).forEach(measure => {
            let measureId = measure.getAttribute("number");
            measure.id =`p${partId}_m${measureId}`;
        });
    });
}

function decorateAllMXML() {
    root = getRoot();

    // Objects that may be present only in one place
    decorateNotesMXML(root);

    findAndDecorateMXML(root, "clef", "attributes/clef");
    findAndDecorateMXML(root, "key", "attributes/key");
    findAndDecorateMXML(root, "time", "attributes/time");
    findAndDecorateMXML(root, "barline", "barline");
    findAndDecorateMXML(root, "rehearsal", "direction/direction-type/rehearsal");
    findAndDecorateMXML(root, "pedal", "direction/direction-type/pedal");

    // Objects that may be present in various places
    findAndDecorateMXML(root, "coda", "barline/coda", "direction/direction-type/coda");
    findAndDecorateMXML(root, "fermata", "barline/fermata", "note/notations/fermata");
    findAndDecorateMXML(root, "segno", "barline/segno", "direction/direction-type/segno");
    findAndDecorateMXML(root, "dynamics", "note/notations/dynamics", "direction/direction-type/dynamics");

    // Objects defined in parts
    decorateBeamsMXML(root)

    findAndDecorateEndToEndMXML(root, "glissando", "note/notations/glissando");
    findAndDecorateEndToEndMXML(root, "slide", "note/notations/slide");
    findAndDecorateEndToEndMXML(root, "slur", "note/notations/slur");
    findAndDecorateEndToEndMXML(root, "tied", "note/notations/tied");
    findAndDecorateEndToEndMXML(root, "tuplet", "note/notations/tuplet");

    findAndDecorateEndToEndMXML(root, "wedge", "direction/direction-type/wedge");
    findAndDecorateEndToEndMXML(root, "octave-shift", "direction/direction-type/octave-shift");
    findAndDecorateEndToEndMXML(root, "bracket", "direction/direction-type/bracket");
    findAndDecorateEndToEndMXML(root, "dashes", "direction/direction-type/dashes");

    decorateMeasures(root);
}

function getRoot() {
    return document.querySelector("score-partwise");
}
