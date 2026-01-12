
/* ====================================================================
   VIEWER APPLICATION - MAIN MODULE

   This module encapsulates all functionality for the Maestro API Viewer.
   It provides a web interface for browsing and searching KernelCI nodes.
   ==================================================================== */

/**
 * Main application namespace to avoid polluting global scope
 */
const ViewerApp = (() => {
    // ================================================================
    // CONFIGURATION
    // ================================================================

    /**
     * Application configuration object
     */
    const CONFIG = {
        // Default search result limit
        SEARCH_LIMIT: 250,

        // Date ranges for quick searches
        WEEK_AGO_DAYS: 7,
        DAY_AGO_DAYS: 1,

        // LAVA instance URL mappings
        LAVA_URLS: {
            'lava-baylibre': 'lava.baylibre.com',
            'lava-broonie': 'lava.sirena.org.uk',
            'lava-cip': 'lava.ciplatform.org',
            'lava-collabora': 'lava.collabora.dev',
            'lava-collabora-early-access': 'staging.lava.collabora.dev',
            'lava-collabora-staging': 'staging.lava.collabora.dev',
            'lava-qualcomm': 'lava.infra.foundries.io',
        },

        // Search operators mapping
        OPERATORS: {
            '>': '__gt=',
            '<': '__lt=',
            '>=': '__gte=',
            '<=': '__lte=',
            '!=': '__ne=',
            '=': '=',
        },

        // Table columns for search results
        TABLE_COLUMNS: ['id', 'kind', 'name', 'platform', 'state', 'result', 'created'],
    };

    // ================================================================
    // STATE MANAGEMENT
    // ================================================================

    /**
     * Application state
     */
    const state = {
        pageBaseUrl: '',
        apiUrl: '',
        weekAgoString: '',
        dayAgoString: '',
    };

    /**
     * Main menu configuration
     */
    let mainMenu = [];

    // ================================================================
    // INITIALIZATION
    // ================================================================

    /**
     * Initialize the application
     * Sets up URLs, date ranges, and renders the initial UI
     */
    function init() {
        try {
            // Initialize URLs
            const url = window.location.href;
            state.pageBaseUrl = url.split('?')[0];
            state.apiUrl = state.pageBaseUrl.replace('/viewer', '');

            // Calculate date ranges for quick searches
            const weekAgo = new Date();
            weekAgo.setDate(weekAgo.getDate() - CONFIG.WEEK_AGO_DAYS);
            state.weekAgoString = weekAgo.toISOString().split('.')[0];

            const dayAgo = new Date();
            dayAgo.setDate(dayAgo.getDate() - CONFIG.DAY_AGO_DAYS);
            state.dayAgoString = dayAgo.toISOString().split('.')[0];

            // Configure main menu
            mainMenu = [
                {
                    name: 'Home',
                    suffix: '',
                },
                {
                    name: 'Node',
                    suffix: '?node_id=',
                },
                {
                    name: 'Search',
                    suffix: '?search=',
                },
                {
                    name: 'Trees',
                    suffix: '?view=trees',
                },
                {
                    name: 'Last week Checkouts',
                    suffix: `?search=kind%3Dcheckout&search=created%3E${state.weekAgoString}`,
                },
                {
                    name: 'Last 24h Checkouts',
                    suffix: `?search=kind%3Dcheckout&search=created%3E${state.dayAgoString}`,
                },
            ];

            // Render the menu
            displayMenu();

            // Parse URL parameters if present
            if (url.indexOf('?') !== -1) {
                parseParameters(url);
            }
        } catch (error) {
            handleError('Failed to initialize application', error);
        }
    }

    // ================================================================
    // UI RENDERING
    // ================================================================

    /**
     * Display the main navigation menu
     */
    function displayMenu() {
        const menu = document.getElementById('menu');
        const menuHtml = mainMenu.map(item =>
            `<a class="menulink" href="${item.suffix}">${item.name}</a>`
        ).join(' ');

        menu.innerHTML = menuHtml;

        // Attach event listeners to menu links
        const links = document.getElementsByClassName('menulink');
        Array.from(links).forEach(link => {
            link.addEventListener('click', handleMenuClick);
        });
    }

    /**
     * Clear all content divs
     */
    function clearDivs() {
        const divIds = ['nodeinfo', 'requestinfo', 'miscbuttons', 'nodesearchdiv', 'treeselector'];
        divIds.forEach(id => {
            const div = document.getElementById(id);
            div.innerHTML = '';
            div.style.display = 'none';
        });
    }

    /**
     * Display error message to user
     * @param {string} message - User-friendly error message
     * @param {Error} error - Error object for console logging
     */
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        document.body.insertBefore(errorDiv, document.getElementById('menu').nextSibling);

        // Auto-remove after 5 seconds
        setTimeout(() => errorDiv.remove(), 5000);
    }

    /**
     * Show modal dialog with message
     * @param {string} message - Message to display
     */
    function showModal(message) {
        const modal = document.getElementById('modal');
        const modalContent = document.getElementById('modalcontent');
        modalContent.textContent = message;
        modal.style.display = 'block';

        // Setup close handlers
        const closeBtn = document.getElementsByClassName('close')[0];
        closeBtn.onclick = () => modal.style.display = 'none';

        window.onclick = (event) => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        };
    }

    /**
     * Hide modal dialog
     */
    function hideModal() {
        const modal = document.getElementById('modal');
        modal.style.display = 'none';
    }

    // ================================================================
    // NODE DISPLAY
    // ================================================================

    /**
     * Display detailed information for a single node
     * @param {string} nodeId - The node ID to display
     */
    async function displayNode(nodeId) {
        try {
            // Hide request info section
            const requestInfo = document.getElementById('requestinfo');
            requestInfo.innerHTML = '';
            requestInfo.style.display = 'none';

            // Fetch node data from API
            const url = `${state.apiUrl}/latest/node/${nodeId}`;
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            const rawText = JSON.stringify(data);

            // Display action buttons
            addMiscButtons(data, rawText);

            // Display formatted JSON
            const nodeInfo = document.getElementById('nodeinfo');
            nodeInfo.style.display = 'block';
            nodeInfo.innerHTML = `<pre>${formatJson(rawText)}</pre>`;

        } catch (error) {
            handleError(`Failed to load node ${nodeId}`, error);
        }
    }

    /**
     * Add action buttons for a node (Parent, Children, Download, LAVA Job)
     * @param {Object} data - Node data object
     * @param {string} raw - Raw JSON string
     */
    function addMiscButtons(data, raw) {
        const miscButtons = document.getElementById('miscbuttons');
        miscButtons.style.display = 'block';

        const buttons = [];

        // Parent button
        if (data.parent) {
            buttons.push(`<button class="misc" data-href="?node_id=${data.parent}">Parent</button>`);
        }

        // Children button
        const childCondition = encodeURIComponent(`parent=${data.id}`);
        buttons.push(`<button class="misc" data-href="?search=${childCondition}">Children</button>`);

        // Artifacts dropdown
        buttons.push(createArtifactsDropdown(data));

        // Download button
        buttons.push('<button id="downloadbutton" class="download">Download</button>');

        // LAVA job button (if applicable)
        if (data.data?.runtime?.startsWith('lava') && data.data?.job_id) {
            const lavaUrl = CONFIG.LAVA_URLS[data.data.runtime];
            if (lavaUrl) {
                const jobUrl = `https://${lavaUrl}/scheduler/job/${data.data.job_id}`;
                buttons.push(`<button class="misc" data-href="${jobUrl}">LAVA Job</button>`);
            }
        }

        // Node size info
        buttons.push(`<span style="margin-left: 10px;">Node size: ${raw.length} bytes</span>`);

        miscButtons.innerHTML = buttons.join('');

        // Attach event listeners
        attachMiscButtonListeners();
    }

    /**
     * Create artifacts dropdown HTML
     * @param {Object} data - Node data object
     * @returns {string} HTML string for artifacts dropdown
     */
    function createArtifactsDropdown(data) {
        const options = [`<option value="${state.apiUrl}/latest/node/${data.id}">Raw node</option>`];

        if (data.artifacts) {
            Object.entries(data.artifacts).forEach(([name, uri]) => {
                options.push(`<option value="${uri}">${name}</option>`);
            });
        }

        return `<select id="artifacts">${options.join('')}</select>`;
    }

    /**
     * Attach event listeners to misc buttons
     */
    function attachMiscButtonListeners() {
        // Misc buttons (navigation)
        const miscLinks = document.getElementsByClassName('misc');
        Array.from(miscLinks).forEach(link => {
            link.addEventListener('click', handleMiscClick);
        });

        // Download button
        const downloadButtons = document.getElementsByClassName('download');
        Array.from(downloadButtons).forEach(button => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                const url = document.getElementById('artifacts').value;
                window.open(url, '_blank');
            });
        });
    }

    // ================================================================
    // SEARCH FUNCTIONALITY
    // ================================================================

    /**
     * Process and execute a search query
     * @param {Array<string>} conditions - Array of search conditions
     */
    async function processSearch(conditions) {
        try {
            // Build search URL
            const conditionParams = conditions
                .map(cond => convertCondition(decodeURIComponent(cond)))
                .join('&');

            const url = `${state.apiUrl}/latest/nodes?${conditionParams}&limit=${CONFIG.SEARCH_LIMIT}`;

            console.log('Search URL:', url);

            // Show loading modal
            showModal('Loading search results...');

            // Fetch search results
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            hideModal();
            displaySearchResults(data);

        } catch (error) {
            hideModal();
            handleError('Search failed', error);
        }
    }

    /**
     * Convert user-friendly search condition to API format
     * @param {string} condition - Search condition (e.g., "created>2024-01-01")
     * @returns {string} Converted condition for API
     */
    function convertCondition(condition) {
        // Pattern: key operator value (e.g., "created>=2024-01-01")
        const pattern = /^([.a-zA-Z0-9_-]+)([<>!=]+)(.*)/;
        const match = pattern.exec(condition);

        if (!match) {
            console.warn('Condition does not match pattern:', condition);
            return condition;
        }

        const [, key, operator, value] = match;
        const apiOperator = CONFIG.OPERATORS[operator] || operator;

        console.log(`Converted: ${key}${operator}${value} -> ${key}${apiOperator}${value}`);
        return `${key}${apiOperator}${value}`;
    }

    /**
     * Display search results in a table
     * @param {Object} data - Search results data
     */
    function displaySearchResults(data) {
        clearDivs();

        const searchDiv = document.getElementById('nodesearchdiv');
        searchDiv.style.display = 'block';

        // Determine table columns based on data
        const columns = [...CONFIG.TABLE_COLUMNS];
        if (data.items.length > 0 && data.items[0].data?.kernel_revision) {
            columns.push('tree', 'branch', 'commit');
        }

        // Sort results by creation date (newest first)
        data.items.sort((a, b) => new Date(b.created) - new Date(a.created));

        // Build table HTML
        const tableHtml = `
            <table class="nodesearch">
                ${createTableHeader(columns)}
                ${createTableRows(data.items)}
            </table>
        `;

        searchDiv.innerHTML = tableHtml;
    }

    /**
     * Create table header HTML
     * @param {Array<string>} columns - Column names
     * @returns {string} Table header HTML
     */
    function createTableHeader(columns) {
        const headers = columns.map(col => `<th>${col}</th>`).join('');
        return `<tr>${headers}</tr>`;
    }

    /**
     * Create table rows HTML
     * @param {Array<Object>} items - Node items
     * @returns {string} Table rows HTML
     */
    function createTableRows(items) {
        return items.map(node => {
            const rowClass = getRowClass(node);
            const cells = createTableCells(node);
            return `<tr class="${rowClass}">${cells}</tr>`;
        }).join('');
    }

    /**
     * Get CSS class for table row based on node result
     * @param {Object} node - Node object
     * @returns {string} CSS class name
     */
    function getRowClass(node) {
        const classes = [];

        if (node.result === 'fail') {
            classes.push('fail');
        } else if (node.result === null && node.state !== 'running') {
            classes.push('null');
        }

        if (node.jobfilter) {
            classes.push('jobfilter');
        }

        return classes.join(' ');
    }

    /**
     * Create table cells HTML for a node
     * @param {Object} node - Node object
     * @returns {string} Table cells HTML
     */
    function createTableCells(node) {
        const cells = [];

        // ID cell with links
        cells.push(`
            <td>
                <a href="?node_id=${node.id}">${node.id}</a>&nbsp;
                <a href="?search=parent%3D${node.id}">(Child nodes)</a>
            </td>
        `);

        // Kind
        cells.push(`<td>${node.kind}</td>`);

        // Name and Platform
        cells.push(`<td>${node.name}</td>`);
        cells.push(`<td>${node.kind === 'job' && node.data?.platform ? node.data.platform : 'N/A'}</td>`);

        // State
        cells.push(`<td>${node.state}</td>`);

        // Result
        cells.push(`<td>${node.result || 'null'}</td>`);

        // Created (with age calculation)
        cells.push(createCreatedCell(node));

        // Kernel revision info (if available)
        if (node.data?.kernel_revision) {
            const kr = node.data.kernel_revision;
            cells.push(`<td>${kr.tree}</td>`);
            cells.push(`<td>${kr.branch}</td>`);
            cells.push(`<td>${kr.commit}</td>`);
        }

        return cells.join('');
    }

    /**
     * Create the 'created' timestamp cell with age information
     * @param {Object} node - Node object
     * @returns {string} Cell HTML
     */
    function createCreatedCell(node) {
        const created = new Date(node.created);
        const now = new Date();
        const timezoneShift = now.getTimezoneOffset() * 60 * 1000;

        let ageText;
        if (node.state !== 'done') {
            // Show time since creation
            const diff = now - created + timezoneShift;
            ageText = `(${formatTimeDiff(diff)} ago)`;
        } else {
            // Show processing duration
            const updated = new Date(node.updated);
            const diff = updated - created;
            ageText = `(${formatTimeDiff(diff)})`;
        }

        return `<td>${node.created}${ageText}</td>`;
    }

    // ================================================================
    // TREES FUNCTIONALITY - KBUILD MATRIX VIEW
    // ================================================================

    /**
     * Display the Trees view with tree selector and kbuild matrix
     *
     * Purpose: Show a matrix of kbuild results across different commits
     * - Rows: kbuild names (e.g., "kbuild-gcc-10-x86", "kbuild-clang-arm64")
     * - Columns: commits (short hash, ordered from oldest to newest)
     * - Cells: build status (pass/fail/running) - clickable to view node details
     *
     * Key Features:
     * - Default lookback period: 4 weeks from current date
     * - Tree filtering with inline search
     * - Handles retry_counter: only shows latest build for each kbuild+commit
     * - Color-coded cells: green=pass, red=fail, orange=running, gray=none
     */
    async function displayTreesView() {
        try {
            clearDivs();

            // Show the tree selector UI
            await displayTreeSelector();

        } catch (error) {
            handleError('Failed to display trees view', error);
        }
    }

    /**
     * Display the tree selector UI with dropdown and search
     *
     * This creates the UI for selecting a tree+branch combination and fetching
     * available combinations from the API. Uses kernel_revision.tree and
     * kernel_revision.branch fields.
     */
    async function displayTreeSelector() {
        const treeSelector = document.getElementById('treeselector');
        treeSelector.style.display = 'block';

        // Initial UI with loading state
        treeSelector.innerHTML = `
            <div>
                <label for="tree-select">Select Tree + Branch:</label>
                <select id="tree-select" disabled>
                    <option>Loading tree/branch combinations...</option>
                </select>
                <input type="text" id="tree-search" placeholder="Search..." style="width: 250px;" disabled>
                <button id="load-tree-button" disabled>Load Matrix</button>
                <span class="loading-spinner"></span>
            </div>
        `;

        // Fetch available tree+branch combinations from API
        const treeBranches = await fetchAvailableTreeBranches();

        // Update UI with tree+branch options
        const treeSelect = document.getElementById('tree-select');
        const treeSearch = document.getElementById('tree-search');
        const loadButton = document.getElementById('load-tree-button');

        treeSelect.disabled = false;
        treeSearch.disabled = false;
        loadButton.disabled = false;

        // Remove loading spinner
        document.querySelector('.loading-spinner')?.remove();

        // Populate dropdown with tree/branch format
        treeSelect.innerHTML = '<option value="">Select a tree/branch...</option>' +
            treeBranches.map(tb => {
                const displayName = `${tb.tree}/${tb.branch}`;
                const value = JSON.stringify(tb);
                return `<option value='${value}'>${displayName}</option>`;
            }).join('');

        // Add search filter functionality
        treeSearch.addEventListener('input', () => {
            const searchTerm = treeSearch.value.toLowerCase();
            Array.from(treeSelect.options).forEach(option => {
                if (option.value === '') return; // Keep the placeholder
                const matches = option.textContent.toLowerCase().includes(searchTerm);
                option.style.display = matches ? '' : 'none';
            });
        });

        // Load matrix when button clicked
        loadButton.addEventListener('click', async () => {
            const selectedValue = treeSelect.value;
            if (!selectedValue) {
                showError('Please select a tree/branch combination');
                return;
            }
            const treeBranch = JSON.parse(selectedValue);
            await loadKbuildMatrix(treeBranch);
        });
    }

    /**
     * Fetch available tree+branch combinations from the API
     *
     * Strategy:
     * 1. Query recent kbuilds (last 4 weeks)
     * 2. Extract unique tree+branch combinations from data.kernel_revision
     * 3. Sort alphabetically by "tree/branch" format
     *
     * @returns {Promise<Array<Object>>} Array of {tree, branch} objects
     */
    async function fetchAvailableTreeBranches() {
        try {
            // Calculate 4 weeks ago date
            // This is the default lookback period for finding active tree/branch combos
            const fourWeeksAgo = new Date();
            fourWeeksAgo.setDate(fourWeeksAgo.getDate() - 28);
            const dateStr = fourWeeksAgo.toISOString().split('.')[0];

            // Query kbuilds from last 4 weeks to find active tree/branch combinations
            const url = `${state.apiUrl}/latest/nodes?kind=kbuild&created__gt=${dateStr}&limit=1000`;
            console.log('Fetching tree/branch combinations from:', url);

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            // Extract unique tree+branch combinations
            // Use a Map to deduplicate by "tree/branch" key
            const treeBranchMap = new Map();
            data.items.forEach(item => {
                const tree = item.data?.kernel_revision?.tree;
                const branch = item.data?.kernel_revision?.branch;

                if (tree && branch) {
                    const key = `${tree}/${branch}`;
                    if (!treeBranchMap.has(key)) {
                        treeBranchMap.set(key, { tree, branch });
                    }
                }
            });

            // Convert to sorted array (sorted by the "tree/branch" display string)
            const treeBranches = Array.from(treeBranchMap.values())
                .sort((a, b) => {
                    const aKey = `${a.tree}/${a.branch}`;
                    const bKey = `${b.tree}/${b.branch}`;
                    return aKey.localeCompare(bKey);
                });

            console.log('Found tree/branch combinations:', treeBranches);

            return treeBranches;

        } catch (error) {
            handleError('Failed to fetch tree/branch combinations', error);
            return [];
        }
    }

    /**
     * Load and display the kbuild matrix for a selected tree+branch combination
     *
     * This is the main function that:
     * 1. Fetches all kbuilds for the tree+branch (last 4 weeks)
     * 2. Organizes data by commit and kbuild name
     * 3. Handles retries (keeps only latest build per kbuild+commit)
     * 4. Renders the matrix table
     *
     * @param {Object} treeBranch - Object with tree and branch properties
     *                              e.g., {tree: "mainline", branch: "master"}
     */
    async function loadKbuildMatrix(treeBranch) {
        try {
            showModal('Loading kbuild matrix...');

            // Calculate 4 weeks ago date
            // This is the lookback range for finding kbuilds
            const fourWeeksAgo = new Date();
            fourWeeksAgo.setDate(fourWeeksAgo.getDate() - 28);
            const dateStr = fourWeeksAgo.toISOString().split('.')[0];

            // Fetch all kbuilds for this tree+branch in the date range
            // IMPORTANT: Filter by BOTH tree AND branch
            const url = `${state.apiUrl}/latest/nodes?kind=kbuild&data.kernel_revision.tree=${treeBranch.tree}&data.kernel_revision.branch=${treeBranch.branch}&created__gt=${dateStr}&limit=1000`;
            console.log('Fetching kbuilds:', url);

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            hideModal();

            const displayName = `${treeBranch.tree}/${treeBranch.branch}`;
            console.log(`Fetched ${data.items.length} kbuilds for ${displayName}`);

            // Process and display the matrix
            displayKbuildMatrix(data.items, displayName);

        } catch (error) {
            hideModal();
            handleError('Failed to load kbuild matrix', error);
        }
    }

    /**
     * Process kbuild data and render the matrix table
     *
     * Matrix Structure:
     * - Rows: kbuild names (unique build configurations)
     * - Columns: commits (short hash, ordered oldest to newest)
     * - Cells: build status with clickable link to node
     *
     * Retry Handling:
     * - Multiple builds may exist for same kbuild+commit (due to retry_counter)
     * - We keep only the LATEST build (highest updated timestamp)
     * - This shows the most recent result for each configuration+commit
     *
     * @param {Array<Object>} kbuilds - Array of kbuild nodes
     * @param {string} displayName - Display name for tree/branch (e.g., "mainline/master")
     */
    function displayKbuildMatrix(kbuilds, displayName) {
        const matrixDiv = document.getElementById('nodesearchdiv');
        matrixDiv.style.display = 'block';

        if (kbuilds.length === 0) {
            matrixDiv.innerHTML = `<p>No kbuilds found for <strong>${displayName}</strong> in the last 4 weeks.</p>`;
            return;
        }

        // ============================================================
        // STEP 1: Extract unique commits and kbuild names
        // ============================================================

        // Commits are stored in data.kernel_revision.commit (full SHA-1)
        // We collect all unique commits and sort by creation date (oldest first)
        const commitMap = new Map(); // commit -> { shortHash, date, fullHash }
        const kbuildNames = new Set(); // Set of unique kbuild names

        kbuilds.forEach(node => {
            const commit = node.data?.kernel_revision?.commit;
            const kbuildName = node.name;

            if (commit && kbuildName) {
                kbuildNames.add(kbuildName);

                // Track commit info - use earliest creation date for sorting
                if (!commitMap.has(commit)) {
                    commitMap.set(commit, {
                        fullHash: commit,
                        shortHash: commit.substring(0, 12), // First 12 chars
                        date: new Date(node.created),
                        describe: node.data.kernel_revision.describe || commit.substring(0, 12)
                    });
                } else {
                    // Update with earlier date if found
                    const existing = commitMap.get(commit);
                    const nodeDate = new Date(node.created);
                    if (nodeDate < existing.date) {
                        existing.date = nodeDate;
                    }
                }
            }
        });

        // Sort commits by date (oldest to newest)
        // This creates a timeline from left to right in the matrix
        const commits = Array.from(commitMap.values()).sort((a, b) => a.date - b.date);
        const kbuildNamesList = Array.from(kbuildNames).sort();

        console.log(`Matrix dimensions: ${kbuildNamesList.length} kbuilds × ${commits.length} commits`);

        // ============================================================
        // STEP 2: Build matrix data structure
        // ============================================================

        // Matrix: kbuildName -> commit -> nodeData
        // For each cell, we store the node information
        const matrix = new Map();

        kbuildNamesList.forEach(name => {
            matrix.set(name, new Map());
        });

        // Populate matrix with nodes
        // IMPORTANT: Handle retries by keeping only the latest build
        kbuilds.forEach(node => {
            const commit = node.data?.kernel_revision?.commit;
            const kbuildName = node.name;

            if (!commit || !kbuildName) return;

            const kbuildRow = matrix.get(kbuildName);
            const existing = kbuildRow.get(commit);

            // Keep only the latest build for this kbuild+commit combination
            // "Latest" is determined by the 'updated' timestamp
            // This handles retry_counter scenarios where multiple builds exist
            if (!existing || new Date(node.updated) > new Date(existing.updated)) {
                kbuildRow.set(commit, {
                    id: node.id,
                    result: node.result,
                    state: node.state,
                    updated: node.updated,
                    retry_counter: node.retry_counter || 0
                });
            }
        });

        // ============================================================
        // STEP 3: Render the matrix table
        // ============================================================

        let tableHtml = `
            <h3>Kbuild Matrix: ${displayName}</h3>
            <p>Showing builds from last 4 weeks (${commits.length} commits, ${kbuildNamesList.length} configurations)</p>
            <div style="overflow-x: auto;">
                <table class="kbuild-matrix">
                    ${createMatrixHeader(commits)}
                    ${createMatrixRows(kbuildNamesList, commits, matrix)}
                </table>
            </div>
        `;

        matrixDiv.innerHTML = tableHtml;

        // Attach click handlers to cells
        attachMatrixCellHandlers();
    }

    /**
     * Create the matrix table header with commit columns
     *
     * Header Structure:
     * - First column: "Kbuild Name"
     * - Remaining columns: Short commit hashes (rotated vertically)
     *
     * Commits are ordered from oldest (left) to newest (right)
     * This creates a timeline view of build results
     *
     * @param {Array<Object>} commits - Array of commit objects with shortHash
     * @returns {string} HTML for table header row
     */
    function createMatrixHeader(commits) {
        const headers = ['<th>Kbuild Name</th>'];

        // Add commit headers
        // Text is rotated vertically to save horizontal space
        commits.forEach(commit => {
            headers.push(`
                <th class="commit-header" title="${commit.describe}">
                    ${commit.shortHash}
                </th>
            `);
        });

        return `<tr>${headers.join('')}</tr>`;
    }

    /**
     * Create matrix table rows with build status cells
     *
     * Each row represents a kbuild configuration (e.g., "kbuild-gcc-10-x86")
     * Each cell shows the build status for that config at that commit
     *
     * Cell States:
     * - Pass: Green background, "PASS" text
     * - Fail: Red background, "FAIL" text
     * - Running: Orange background, "RUN" text
     * - None: Gray background, "-" text (no build for this commit)
     *
     * Cells are clickable and navigate to the node detail view
     *
     * @param {Array<string>} kbuildNames - Array of kbuild configuration names
     * @param {Array<Object>} commits - Array of commit objects
     * @param {Map} matrix - Matrix data structure (kbuild -> commit -> node)
     * @returns {string} HTML for table body rows
     */
    function createMatrixRows(kbuildNames, commits, matrix) {
        const rows = [];

        kbuildNames.forEach(kbuildName => {
            const cells = [`<td>${kbuildName}</td>`];
            const kbuildRow = matrix.get(kbuildName);

            commits.forEach(commit => {
                const node = kbuildRow.get(commit.fullHash);

                if (node) {
                    // Build exists for this kbuild+commit
                    const statusClass = getStatusClass(node);
                    const statusText = getStatusText(node);

                    // data-node-id attribute allows click handler to navigate
                    cells.push(`
                        <td class="build-cell ${statusClass}" data-node-id="${node.id}" title="Retry: ${node.retry_counter}">
                            ${statusText}
                        </td>
                    `);
                } else {
                    // No build for this kbuild+commit combination
                    cells.push('<td class="build-cell build-none">-</td>');
                }
            });

            rows.push(`<tr>${cells.join('')}</tr>`);
        });

        return rows.join('');
    }

    /**
     * Get CSS class for build status
     *
     * @param {Object} node - Node data with result and state
     * @returns {string} CSS class name
     */
    function getStatusClass(node) {
        if (node.result === 'pass') return 'build-pass';
        if (node.result === 'fail') return 'build-fail';
        if (node.state === 'running') return 'build-running';
        return 'build-none';
    }

    /**
     * Get display text for build status
     *
     * @param {Object} node - Node data with result and state
     * @returns {string} Status text
     */
    function getStatusText(node) {
        if (node.result === 'pass') return 'PASS';
        if (node.result === 'fail') return 'FAIL';
        if (node.state === 'running') return 'RUN';
        return '?';
    }

    /**
     * Attach click handlers to matrix cells
     *
     * When a cell is clicked, navigate to the node detail view
     * This allows users to drill down into specific build results
     */
    function attachMatrixCellHandlers() {
        const cells = document.querySelectorAll('.build-cell[data-node-id]');
        cells.forEach(cell => {
            cell.addEventListener('click', () => {
                const nodeId = cell.getAttribute('data-node-id');
                if (nodeId) {
                    // Navigate to node detail view
                    const fullUrl = `${state.pageBaseUrl}?node_id=${nodeId}`;
                    window.history.pushState('', '', fullUrl);
                    displayNode(nodeId);
                }
            });
        });
    }

    // ================================================================
    // USER INTERACTION HANDLERS
    // ================================================================

    /**
     * Handle menu link clicks
     * @param {Event} event - Click event
     */
    function handleMenuClick(event) {
        event.preventDefault();
        const href = this.getAttribute('href');
        const fullUrl = state.pageBaseUrl + href;
        window.history.pushState('', '', fullUrl);
        parseParameters(fullUrl);
    }

    /**
     * Handle misc button clicks (Parent, Children, LAVA Job)
     * @param {Event} event - Click event
     */
    function handleMiscClick(event) {
        event.preventDefault();
        const href = this.getAttribute('data-href');

        // Open external links in new tab
        if (href.startsWith('http')) {
            window.open(href, '_blank');
        } else {
            // Navigate internally
            const fullUrl = state.pageBaseUrl + href;
            window.history.pushState('', '', fullUrl);
            parseParameters(fullUrl);
        }

        console.log('Navigation:', href);
    }

    /**
     * Display node ID request form
     */
    function requestNodeId() {
        const requestInfo = document.getElementById('requestinfo');
        requestInfo.innerHTML = `
            <input type="text" id="nodeid" value="" placeholder="65b09399b198ea6cb7bbffda">
            <button id="nodeidbutton">Request</button>
        `;
        requestInfo.style.display = 'block';

        // Attach event listener
        document.getElementById('nodeidbutton').addEventListener('click', (event) => {
            event.preventDefault();
            const nodeId = document.getElementById('nodeid').value.trim();

            if (!nodeId) {
                showError('Node ID cannot be empty');
                return;
            }

            const fullUrl = `${state.pageBaseUrl}?node_id=${nodeId}`;
            window.history.pushState('', '', fullUrl);
            displayNode(nodeId);
        });

        // Clear other sections
        const nodeInfo = document.getElementById('nodeinfo');
        nodeInfo.innerHTML = '';
        nodeInfo.style.display = 'none';
    }

    /**
     * Parse URL parameters and route to appropriate handler
     * @param {string} url - Full URL to parse
     */
    function parseParameters(url) {
        const queryString = url.split('?')[1];

        if (!queryString) {
            clearDivs();
            return;
        }

        const parameters = queryString.split('&');

        // Check for view parameter (e.g., view=trees)
        for (const param of parameters) {
            const [key, value] = param.split('=');

            if (key === 'view' && value === 'trees') {
                displayTreesView();
                return;
            }

            if (key === 'node_id') {
                if (!value) {
                    requestNodeId();
                } else {
                    displayNode(value);
                }
                return;
            }

            if (key === 'search') {
                // Collect all search conditions
                const conditions = parameters
                    .filter(p => p.startsWith('search='))
                    .map(p => p.split('=')[1]);

                processSearch(conditions);
                return;
            }
        }

        // Unknown parameter
        console.warn('Unknown parameter in URL:', parameters[0]);
        showError('Unknown parameter in URL');
        clearDivs();
    }

    // ================================================================
    // UTILITY FUNCTIONS
    // ================================================================

    /**
     * Format JSON with indentation
     * @param {string} jsonText - JSON string
     * @returns {string} Formatted JSON
     */
    function formatJson(jsonText) {
        try {
            const json = JSON.parse(jsonText);
            return JSON.stringify(json, null, 2);
        } catch (error) {
            console.error('Failed to parse JSON:', error);
            return jsonText;
        }
    }

    /**
     * Format time difference into human-readable string
     * @param {number} diff - Time difference in milliseconds
     * @returns {string} Formatted time string (e.g., "2h 30m")
     */
    function formatTimeDiff(diff) {
        const hours = Math.floor(diff / (1000 * 60 * 60)) % 24;
        const minutes = Math.floor(diff / (1000 * 60)) % 60;

        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    }

    /**
     * Handle errors with user feedback and console logging
     * @param {string} message - User-friendly error message
     * @param {Error} error - Error object
     */
    function handleError(message, error) {
        console.error(message, error);
        showError(`${message}: ${error.message}`);
    }

    // ================================================================
    // PUBLIC API
    // ================================================================

    return {
        init,
    };
})();

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', ViewerApp.init);
