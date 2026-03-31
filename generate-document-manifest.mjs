import fs from 'fs';
import path from 'path';

// sessionId passed as CLI arg, defaults to 2
const sessionId = process.argv[2] || '2';

const documentTypes = [
    { dirName: `amendment-pdfs-${sessionId}`, key: 'amendments' },
    { dirName: `fiscal-note-pdfs-${sessionId}`, key: 'fiscal-notes' },
    { dirName: `legal-note-pdfs-${sessionId}`, key: 'legal-notes' },
];

const downloadsDir = path.join(process.cwd(), 'interface', 'downloads');
const outputDir = path.join(process.cwd(), 'output');

// ensure output dir exists
if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

console.log(`Generating document manifest for session ${sessionId}...`);

const documentIndex = {};
const billsWithAmendments = [];

documentTypes.forEach(({ dirName, key }) => {
    const typeDir = path.join(downloadsDir, dirName);
    if (!fs.existsSync(typeDir)) {
        console.log(`Directory doesn't exist: ${typeDir}`);
        documentIndex[key] = {};
        return;
    }

    documentIndex[key] = {};
    console.log(`Scanning ${dirName}...`);

    try {
        const billDirs = fs.readdirSync(typeDir);

        billDirs.forEach(billDir => {
            const billPath = path.join(typeDir, billDir);
            if (!fs.statSync(billPath).isDirectory()) return;

            const files = fs.readdirSync(billPath)
                .filter(file => file.toLowerCase().endsWith('.pdf'))
                .map(file => {
                    let name = file.replace(/\.pdf$/i, '');

                    // extract any parenthetical suffixes like (1), (2) etc.
                    const suffixMatch = file.match(/\((\d+)\)\.pdf$/i);
                    const suffix = suffixMatch ? `(${suffixMatch[1]})` : '';

                    // special handling for HB-2 with section letters
                    if (billDir === 'HB-2') {
                        const sectionPattern = /([A-Z]{2})0*(\d+)\.(\d+)\.(\d+)\.([A-Z])\.(\d+)_[^_]+_(final-\w+)(?:\.pdf)?/i;
                        const sectionMatch = file.match(sectionPattern);

                        if (sectionMatch) {
                            const [_, prefix, billNum, major, minor, sectionLetter, amendNum, finalType] = sectionMatch;

                            const sectionMap = {
                                'A': 'general-government',
                                'B': 'health',
                                'C': 'nat-resource-transportation',
                                'D': 'public-safety',
                                'E': 'k-12-education',
                                'F': 'long-range',
                                'O': 'global-amendment'
                            };

                            const sectionName = sectionMap[sectionLetter.toUpperCase()] || sectionLetter;
                            name = `${prefix}-${billNum}.${major}.${minor}.${sectionLetter}.${amendNum}.${sectionName}.${finalType}${suffix}`;

                            return {
                                name,
                                url: `/capitol-tracker-2025/${key}/${billDir}/${encodeURIComponent(file)}`
                            };
                        }
                    }

                    // standard processing for all other bills
                    const matches = file.match(/([A-Z]{2})0*(\d+)((?:\.\d+)+(?:\.[A-Z]\.\d+)*)_[^_]+_(final-\w+)(?:\.pdf)?/i);
                    if (matches) {
                        const [_, prefix, billNum, versionInfo, finalType] = matches;
                        name = `${prefix}-${billNum}${versionInfo}.${finalType}${suffix}`;
                    }

                    return {
                        name,
                        url: `/capitol-tracker-2025/${key}/${billDir}/${encodeURIComponent(file)}`
                    };
                })
                .sort((a, b) => a.name.localeCompare(b.name));

            documentIndex[key][billDir] = files;
        });
    } catch (error) {
        console.error(`Error processing ${dirName}:`, error);
        documentIndex[key] = {};
    }
});

// build bills-with-amendments list
if (documentIndex.amendments) {
    Object.keys(documentIndex.amendments).forEach(billId => {
        if (documentIndex.amendments[billId].length > 0) {
            billsWithAmendments.push(billId.replace('-', ' '));
        }
    });
}

billsWithAmendments.sort((a, b) => {
    const [aType, aNumStr] = a.split(' ');
    const [bType, bNumStr] = b.split(' ');
    if (aType !== bType) return aType.localeCompare(bType);
    return parseInt(aNumStr, 10) - parseInt(bNumStr, 10);
});

const billsWithAmendmentsPath = path.join(outputDir, 'bills-with-amendments.txt');
fs.writeFileSync(billsWithAmendmentsPath, billsWithAmendments.join('\n'), 'utf8');
console.log(`Generated bills-with-amendments list with ${billsWithAmendments.length} bills`);

const outputPath = path.join(outputDir, 'document-index.json');
fs.writeFileSync(outputPath, JSON.stringify(documentIndex, null, 2));
console.log(`Document manifest created at ${outputPath}`);
