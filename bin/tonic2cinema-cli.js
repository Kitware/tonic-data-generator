#! /usr/bin/env node

var fs = require('fs'),
    path = require('path'),
    usage = 'Usage: Tonic2Cinema /path/to/Tonic/DataSet/directory';

// Make sure we have valid argument
if(process.argv.length !== 3) {
    console.log(usage);
    return;
}

// Load Tonic descriptor
var tonicDescriptor = require(process.argv[2] + '/index.json');

// Find the possible type mapping
if(tonicDescriptor.type.length === 1 && tonicDescriptor.type[0] === 'tonic-query-data-model') {
    // Spec A
    require('../javascript/tonic-cinema-spec-a').cinema(tonicDescriptor, process.argv[2]);
} else {
    console.log('The following Tonic dataset can not be converted into Cinema database.');
    console.log('=>', tonicDescriptor.type);
}
