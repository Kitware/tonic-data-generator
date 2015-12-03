var fs = require('fs'),
    path = require('path'),
    reservedNames = {
        'phi':   'Camera_X',
        'theta': 'Camera_Y'
    },
    tonicBinds = {
        theta: {
            mouse: { drag: { modifier: 0, coordinate: 1, step: 30, orientation: +1 } }
        },
        phi: {
            mouse: { drag: { modifier: 0, coordinate: 0, step: 10, orientation: +1 } }
        },
    };

function convertTonicQueryDataModelToCinemaSpecA(tonicMetadata, destinationDirectory) {
    var cinemaFormat = {
        type: "simple",
        version: "1.1",
        metadata: {
            type: "parametric-image-stack"
        },
        name_pattern: tonicMetadata.data[0].pattern,
        arguments: {}
    }

    // Register each arguments
    for(var name in tonicMetadata.arguments) {
        var cinemaArg = {};

        // Add values
        cinemaArg.label = name; // Cinema does not support (label != name)
        cinemaArg.type = tonicMetadata.arguments[name].ui ? (tonicMetadata.arguments[name].ui === 'slider' ? 'range' : 'list') : 'list';
        cinemaArg.values = tonicMetadata.arguments[name].values;
        cinemaArg.default = cinemaArg.values[tonicMetadata.arguments[name].default || 0];

        if(reservedNames[name]) {
            cinemaFormat.name_pattern = cinemaFormat.name_pattern.replace('{'+name+'}','{' + reservedNames[name] + '}');
            name = cinemaArg.label = reservedNames[name];
        }

        cinemaFormat.arguments[name] = cinemaArg;
    }

    // Write into info.json
    var outputFilename = path.join(destinationDirectory, 'info.json');
    fs.writeFile(outputFilename, JSON.stringify(cinemaFormat, null, 2), function(err) {
        if(err) {
            console.log(err);
        } else {
            console.log("Dataset converted and Cinema Store saved to " + outputFilename);
        }
    });
}

function convertCinemaArgToTonic(argName, cinemaArg) {
    var tonicArg = {};

    // Fill data if needed
    tonicArg.values = cinemaArg.values;
    if(cinemaArg.values.indexOf(cinemaArg.default) > 0) {
        tonicArg.default = cinemaArg.values.indexOf(cinemaArg.default);
    }
    if(cinemaArg.type === 'range') {
        tonicArg.ui  = 'slider';
    }
    if(cinemaArg.label !== argName) {
        tonicArg.label = cinemaArg.label;
    }

    // Add default binding
    if(tonicBinds[argName]) {
        tonicArg.bind = tonicBinds[argName];
    }

    // Add default looping
    if(argName === 'phi') {
        tonicArg.loop = 'modulo';
    }

    return tonicArg;
}

function convertCinemaSpecAToTonic(cinemaMetadata, destinationDirectory) {
    var tonicFormat = {
        type: [ 'tonic-query-data-model' ],
        arguments_order: [],
        arguments: {},
        data: [{ name: "image", type: "blob", mimeType: "image/", pattern: cinemaMetadata.name_pattern }],
        metadata: {}
    };

    // Extract mime type
    var patternList = cinemaMetadata.name_pattern.split('.');
    tonicFormat.data[0].mimeType += patternList[patternList.length - 1];

    // Process arguments
    for(var argName in cinemaMetadata.arguments) {
        var cinemaArg = cinemaMetadata.arguments[argName],
            tonicArg = convertCinemaArgToTonic(argName, cinemaArg);

        if(tonicArg.values.length > 1) {
            tonicFormat.arguments_order.push(argName);
        }
        tonicFormat.arguments[argName] = tonicArg;
    }

    // Process metadata
    for(var metaKey in cinemaMetadata.metadata) {
        if(metaKey !== 'type') {
            tonicFormat.metadata[metaKey] = cinemaMetadata.metadata[metaKey];
        }
    }

    // Write into cinema.json
    var outputFilename = path.join(destinationDirectory, 'index.json');
    fs.writeFile(outputFilename, JSON.stringify(tonicFormat, null, 2), function(err) {
        if(err) {
            console.log(err);
        } else {
            console.log("Dataset converted from Cinema Store Spec A to Tonic dataset: " + outputFilename);
        }
    });
}

module.exports = {
    cinema: convertTonicQueryDataModelToCinemaSpecA,
    tonic: convertCinemaSpecAToTonic,
    tonicArg: convertCinemaArgToTonic
};