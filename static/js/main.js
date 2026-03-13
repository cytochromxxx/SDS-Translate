
        // Global state
        let currentFile = null;
        let translatedContent = null;

        // Tab switching
        function showTab(tabName, btnElement) {
            // Update tabs
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            if (btnElement) btnElement.classList.add('active');

            // Update content
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            document.getElementById(tabName + '-tab').classList.add('active');

            if (tabName === 'stats') {
                loadStats();
            }
        }

        // File selection handler
        function handleFileSelect(input) {
            const file = input.files[0];
            const label = document.getElementById('fileLabel');
            const fileName = document.getElementById('fileName');

            if (file) {
                fileName.textContent = `📄 ${file.name} (${(file.size/1024).toFixed(1)} KB)`;
                label.classList.add('has-file');
                uploadFile(file);
            } else {
                fileName.textContent = 'Keine Datei ausgewählt';
                label.classList.remove('has-file');
            }
        }

        let isOriginalEditMode = false;
        let originalContentBeforeEdit = '';

        function toggleEditMode(type) {
            const isOriginal = type === 'original';
            let currentEditMode = isOriginal ? isOriginalEditMode : isEditMode;
            currentEditMode = !currentEditMode;
            if(isOriginal) {
                isOriginalEditMode = currentEditMode;
            } else {
                isEditMode = currentEditMode;
            }

            const container = document.getElementById(isOriginal ? 'originalPreview' : 'translatedPreview').closest('.preview-box');
            const editContainer = document.getElementById(isOriginal ? 'originalEditModeContainer' : 'editModeContainer');
            const previewFrame = document.getElementById(isOriginal ? 'originalPreview' : 'translatedPreview');
            const editor = document.getElementById(isOriginal ? 'originalRichTextEditor' : 'richTextEditor');
            const btn = document.getElementById(isOriginal ? 'editOriginalBtn' : 'editModeBtn');
            const toolbar = document.getElementById(isOriginal ? 'originalEditModeToolbar' : 'editModeToolbar');

            if (currentEditMode) {
                let content = previewFrame.srcdoc;
                if(isOriginal) {
                    originalContentBeforeEdit = content;
                } else {
                    originalTranslatedContent = content;
                }
                editor.innerHTML = content;
                container.classList.add('edit-mode-active');
                editContainer.style.display = 'block';
                toolbar.style.display = 'flex';
                previewFrame.style.display = 'none';
                btn.classList.add('active');
                btn.innerHTML = '👁️ Vorschau';
            } else {
                container.classList.remove('edit-mode-active');
                editContainer.style.display = 'none';
                toolbar.style.display = 'none';
                previewFrame.style.display = 'block';
                btn.classList.remove('active');
                btn.innerHTML = '✏️ Bearbeiten';
            }
        }

        function execEditCmd(command, value = null) {
            // Determine which editor to use
            let editor;
            if (isModalOpen) {
                editor = document.getElementById('modalRichTextEditor');
            } else if (value === 'original' || (typeof value === 'object' && value !== null && value.target === 'original')) {
                // Handle both execEditCmd('bold', 'original') and execEditCmd('bold', {target: 'original'})
                editor = document.getElementById('originalRichTextEditor');
            } else if (isOriginalEditMode) {
                editor = document.getElementById('originalRichTextEditor');
            } else {
                editor = document.getElementById('richTextEditor');
            }

            if (editor) {
                document.execCommand(command, false, value === 'original' || (typeof value === 'object' && value !== null && value.target === 'original') ? null : value);
                editor.focus();
            }
        }

        // Helper function to exec command with specific editor
        function execEditCmdForEditor(command, editorId, value = null) {
            const editor = document.getElementById(editorId);
            if (editor) {
                document.execCommand(command, false, value);
                editor.focus();
            }
        }

        async function saveChanges(type) {
            const isOriginal = type === 'original';
            const editor = document.getElementById(isOriginal ? 'originalRichTextEditor' : 'richTextEditor');
            const newContent = editor.innerHTML;
            const url = isOriginal ? '/api/save/original' : '/api/save/translated';

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: newContent }),
                });
                const result = await response.json();
                if (result.success) {
                    showToast('Änderungen gespeichert!', 'success');
                    document.getElementById(isOriginal ? 'originalPreview' : 'translatedPreview').srcdoc = newContent;
                    toggleEditMode(type);
                } else {
                    showToast('Fehler beim Speichern: ' + result.error, 'error');
                }
            } catch (error) {
                showToast('Fehler: ' + error.message, 'error');
            }
        }

        function discardChanges(type) {
            if (confirm('Änderungen verwerfen?')) {
                const isOriginal = type === 'original';
                const editor = document.getElementById(isOriginal ? 'originalRichTextEditor' : 'richTextEditor');
                editor.innerHTML = isOriginal ? originalContentBeforeEdit : originalTranslatedContent;
                toggleEditMode(type);
            }
        }

        // Current file type (html, pdf, or xml)
        let currentFileType = 'html';

        // Select file type (HTML, PDF, or XML)
        function selectFileType(type) {
            currentFileType = type;

            // Update button states
            document.getElementById('btnHtml').classList.toggle('active', type === 'html');
            document.getElementById('btnPdf').classList.toggle('active', type === 'pdf');
            document.getElementById('btnXml').classList.toggle('active', type === 'xml');

            // Show/hide appropriate input sections
            document.getElementById('htmlInputSection').style.display = type === 'html' ? 'block' : 'none';
            document.getElementById('pdfInputSection').style.display = type === 'pdf' ? 'block' : 'none';
            document.getElementById('xmlInputSection').style.display = type === 'xml' ? 'block' : 'none';

            // Reset UI elements
            document.getElementById('pdfInfo').style.display = 'none';
            document.getElementById('progressSection').style.display = 'none';
        }

        // PDF file selection handler
        async function handlePdfFileSelect(input) {
            const file = input.files[0];
            const label = document.getElementById('pdfFileLabel');
            const fileName = document.getElementById('pdfFileName');

            if (file) {
                fileName.textContent = `📕 ${file.name} (${(file.size/1024/1024).toFixed(1)} MB)`;
                label.classList.add('has-file');

                // Process PDF file
                await processPdfFile(file);
            } else {
                fileName.textContent = 'Keine PDF-Datei ausgewählt';
                label.classList.remove('has-file');
            }
        }

        // XML file selection handler
        async function handleXmlFileSelect(input) {
            const file = input.files[0];
            const label = document.getElementById('xmlFileLabel');
            const fileName = document.getElementById('xmlFileName');

            if (file) {
                fileName.textContent = `🗂️ ${file.name} (${(file.size/1024).toFixed(1)} KB)`;
                label.classList.add('has-file');

                // Process XML file
                await processXmlFile(file);
            } else {
                fileName.textContent = 'Keine XML-Datei ausgewählt';
                label.classList.remove('has-file');
            }
        }

        // Upload and process XML file
        async function processXmlFile(file) {
            const formData = new FormData();
            formData.append('file', file);

            const progressSection = document.getElementById('progressSection');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');

            progressSection.style.display = 'block';
            progressFill.style.width = '0%';
            progressText.textContent = 'Lade XML hoch...';

            try {
                const response = await fetch('/api/sdscom/process', {
                    method: 'POST',
                    body: formData
                });

                progressText.textContent = 'Verarbeite XML...';
                progressFill.style.width = '50%';

                const result = await response.json();

                if (response.ok) {
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Import erfolgreich!';

                    document.getElementById('uploadStatus').innerHTML = `
                        <div class="alert alert-success">
                            ✅ <strong>${file.name}</strong> erfolgreich importiert.
                            <br>Produkt: <span class="highlight">${result.product_name}</span>
                        </div>`;

                    // Display previews
                    const originalPreview = document.getElementById('originalPreview');
                    originalPreview.srcdoc = result.preview;

                    document.getElementById('previewContainer').style.display = 'grid';
                    document.getElementById('translateBtn').disabled = false;

                    // Hide the translated preview initially
                    document.getElementById('translatedPreview').srcdoc = '';
                    document.getElementById('statsCard').style.display = 'none';
                    document.getElementById('downloadNotFoundSection').style.display = 'none';

                } else {
                    throw new Error(result.error || 'Unbekannter Fehler beim XML-Import');
                }

            } catch (error) {
                progressText.textContent = 'Import fehlgeschlagen!';
                progressFill.style.background = 'var(--error)';
                document.getElementById('uploadStatus').innerHTML = `
                    <div class="alert alert-error">
                        ❌ Fehler beim XML-Import: ${error.message}
                    </div>`;
            }
        }

        // Upload and process PDF file
        async function processPdfFile(file) {
            const formData = new FormData();
            formData.append('file', file);

            const progressSection = document.getElementById('progressSection');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');

            progressSection.style.display = 'block';
            progressFill.style.width = '0%';
            progressText.textContent = 'Lade PDF hoch...';

            try {
                const response = await fetch('/api/pdf/process', {
                    method: 'POST',
                    body: formData
                });

                progressText.textContent = 'Verarbeite PDF...';
                progressFill.style.width = '50%';

                const result = await response.json();

                if (response.ok) {
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Import erfolgreich!';

                    document.getElementById('uploadStatus').innerHTML = `
                        <div class="alert alert-success">
                            ✅ <strong>${file.name}</strong> erfolgreich importiert.
                            <br>Produkt: <span class="highlight">${result.product_name}</span>
                        </div>`;

                    // Display previews
                    const originalPreview = document.getElementById('originalPreview');
                    originalPreview.srcdoc = result.preview;

                    document.getElementById('previewContainer').style.display = 'grid';
                    document.getElementById('translateBtn').disabled = false;

                    // Hide the translated preview initially
                    document.getElementById('translatedPreview').srcdoc = '';
                    document.getElementById('statsCard').style.display = 'none';
                    document.getElementById('downloadNotFoundSection').style.display = 'none';

                } else {
                    throw new Error(result.error || 'Unbekannter Fehler beim PDF-Import');
                }

            } catch (error) {
                progressText.textContent = 'Import fehlgeschlagen!';
                progressFill.style.background = 'var(--error)';
                document.getElementById('uploadStatus').innerHTML = `
                    <div class="alert alert-error">
                        ❌ Fehler beim PDF-Import: ${error.message}
                    </div>`;
            }
        }

        // Upload function for HTML files
        async function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();

                if (response.ok) {
                    document.getElementById('uploadStatus').innerHTML = `
                        <div class="alert alert-success">
                            ✅ Datei <strong>${result.filename}</strong> (${(result.size/1024).toFixed(1)} KB) geladen.
                        </div>`;

                    currentFile = file.name;

                    const originalPreview = document.getElementById('originalPreview');
                    originalPreview.srcdoc = result.preview;

                    document.getElementById('previewContainer').style.display = 'grid';
                    document.getElementById('translateBtn').disabled = false;

                    document.getElementById('translatedPreview').srcdoc = '';
                    document.getElementById('statsCard').style.display = 'none';
                    document.getElementById('downloadNotFoundSection').style.display = 'none';
                } else {
                    document.getElementById('uploadStatus').innerHTML = `<div class="alert alert-error">❌ ${result.error}</div>`;
                }
            } catch (error) {
                document.getElementById('uploadStatus').innerHTML = `<div class="alert alert-error">❌ Fehler beim Upload: ${error.message}</div>`;
            }
        }

        // Translate function
        async function translateFile() {
            const language = document.getElementById('languageSelect').value;
            const translateBtn = document.getElementById('translateBtn');
            translateBtn.disabled = true;
            translateBtn.innerHTML = '... Übersetze ...';

            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ language })
                });

                const result = await response.json();

                if (response.ok) {
                    // Debug: Log preview length
                    console.log('Preview length:', result.preview ? result.preview.length : 0);

                    if (result.preview && result.preview.length > 0) {
                        document.getElementById('translatedPreview').srcdoc = result.preview;
                        translatedContent = result.preview;
                    } else {
                        showToast('Warnung: Keine Vorschau verfügbar', 'warning');
                    }

                    // Update stats
                    const stats = result.stats;
                    document.getElementById('totalTexts').textContent = stats.total_texts;
                    document.getElementById('translatedCount').textContent = stats.translated_exact;
                    document.getElementById('notFoundCount').textContent = stats.not_found;

                    const coverage = (stats.translated_exact / stats.total_texts * 100) || 0;
                    const coverageBar = document.getElementById('coverageBar');
                    coverageBar.style.width = `${coverage.toFixed(1)}%`;
                    coverageBar.textContent = `${coverage.toFixed(1)}%`;

                    // Display not found phrases
                    const notFoundList = document.getElementById('notFoundList');
                    const notFoundBadge = document.getElementById('notFoundBadge');
                    notFoundList.innerHTML = '';
                    notFoundBadge.textContent = result.not_found.length;

                    if (result.not_found.length > 0) {
                        result.not_found.forEach(phrase => {
                            const item = document.createElement('div');
                            item.className = 'phrase-item';
                            item.innerHTML = `
                                <div class="phrase-content">
                                    <span class="phrase-text">${phrase.text}</span>
                                    <span class="phrase-line">Line: ${phrase.line}</span>
                                </div>
                                <div class="phrase-actions">
                                    <button class="secondary" style="padding: 4px 8px;" onclick="showAddModalWithText('${phrase.text.replace(/'/g, "\\'")}')">➕</button>
                                </div>`;
                            notFoundList.appendChild(item);
                        });
                    } else {
                        notFoundList.innerHTML = '<div style="text-align: center; color: var(--text-secondary);">🎉 Alle Phrasen gefunden!</div>';
                    }

                    document.getElementById('statsCard').style.display = 'block';
                    document.getElementById('downloadNotFoundSection').style.display = 'flex';

                } else {
                    showToast(`Übersetzungsfehler: ${result.error}`, 'error');
                }

            } catch (error) {
                showToast(`Fehler: ${error.message}`, 'error');
            } finally {
                translateBtn.disabled = false;
                translateBtn.innerHTML = '🚀 Übersetzen starten';
            }
        }

        // Refresh preview
        function refreshPreview(type) {
            const iframe = document.getElementById(type === 'original' ? 'originalPreview' : 'translatedPreview');
            const url = type === 'original' ? '/api/preview/original' : '/api/preview/translated';

            fetch(url)
                .then(response => response.json())
                .then(data => {
                    iframe.srcdoc = data.content;
                    if (type === 'translated') {
                        translatedContent = data.content;
                    }
                    showToast(`${type.charAt(0).toUpperCase() + type.slice(1)} preview refreshed`, 'info');
                })
                .catch(error => {
                    showToast(`Error refreshing preview: ${error}`, 'error');
                });
        }

        // Download functions
        function downloadHTML() {
            window.location.href = '/api/download';
        }

        function downloadPDF() {
            showToast('PDF-Generierung gestartet...', 'info');

            fetch('/api/download/pdf')
                .then(response => {
                    if (response.ok) {
                        return response.blob();
                    } else {
                        return response.json().then(err => { throw new Error(err.error) });
                    }
                })
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = `translated_sds.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    showToast('PDF-Download erfolgreich!', 'success');
                })
                .catch(error => {
                    showToast(`PDF-Fehler: ${error.message}`, 'error');
                });
        }

        // Edit Mode
        let isEditMode = false;
        let originalTranslatedContent = '';
        let currentZoom = 100;

        let isModalOpen = false;

        function toggleFullscreenEdit() {
            const modal = document.getElementById('editModalOverlay');
            isModalOpen = !isModalOpen;

            if (isModalOpen) {
                document.getElementById('modalRichTextEditor').innerHTML = document.getElementById('richTextEditor').innerHTML;
                modal.classList.add('active');
            } else {
                modal.classList.remove('active');
            }
        }

        function closeEditModal() {
            document.getElementById('editModalOverlay').classList.remove('active');
            isModalOpen = false;
        }

        function saveChangesInModal() {
            const newContent = document.getElementById('modalRichTextEditor').innerHTML;
            document.getElementById('richTextEditor').innerHTML = newContent;
            saveChanges('translated');
            closeEditModal();
        }

        function discardChangesInModal() {
            if (confirm('Änderungen im Vollbildmodus verwerfen?')) {
                closeEditModal();
            }
        }

        function zoomEdit(amount) {
            currentZoom += amount;
            if (currentZoom < 50) currentZoom = 50;
            if (currentZoom > 200) currentZoom = 200;

            const editor = document.getElementById(isModalOpen ? 'modalRichTextEditor' : 'richTextEditor');
            editor.style.zoom = `${currentZoom}%`;
            document.getElementById(isModalOpen ? 'modalZoomLevel' : 'zoomLevel').textContent = `${currentZoom}%`;
        }

        // Zoom level for original editor
        let originalZoomLevel = 100;

        // Function to exec command for original editor
        function execEditCmdForOriginal(command, value = null) {
            const editor = document.getElementById('originalRichTextEditor');
            if (editor) {
                document.execCommand(command, false, value);
                editor.focus();
            }
        }

        // Function to zoom original editor
        function zoomEditOriginal(amount) {
            originalZoomLevel += amount;
            if (originalZoomLevel < 50) originalZoomLevel = 50;
            if (originalZoomLevel > 200) originalZoomLevel = 200;

            const editor = document.getElementById('originalRichTextEditor');
            if (editor) {
                editor.style.zoom = `${originalZoomLevel}%`;
            }
            document.getElementById('originalZoomLevel').textContent = `${originalZoomLevel}%`;
        }

        // WYSIWYG table functions
        function insertTable(rows, cols) {
            let table = '<table class="sds" style="width:100%; border-collapse:collapse;">';
            for (let i = 0; i < rows; i++) {
                table += '<tr>';
                for (let j = 0; j < cols; j++) {
                    table += '<td style="border:1px solid black; padding:5px;">&nbsp;</td>';
                }
                table += '</tr>';
            }
            table += '</table><p>&nbsp;</p>';
            execEditCmd('insertHTML', table);
        }

        function getSelectedCell() {
            let sel = window.getSelection();
            if (sel.rangeCount > 0) {
                let node = sel.getRangeAt(0).startContainer;
                while (node && !['TD', 'TH'].includes(node.tagName)) {
                    node = node.parentNode;
                }
                return node;
            }
            return null;
        }

        function addTableRow() {
            const cell = getSelectedCell();
            if (!cell) return;
            const table = cell.closest('table');
            const rowIndex = cell.parentNode.rowIndex;
            const newRow = table.insertRow(rowIndex + 1);
            for (let i = 0; i < cell.parentNode.cells.length; i++) {
                newRow.insertCell(i).innerHTML = '&nbsp;';
            }
        }

        function addTableColumn() {
            const cell = getSelectedCell();
            if (!cell) return;
            const table = cell.closest('table');
            const cellIndex = cell.cellIndex;
            for (let i = 0; i < table.rows.length; i++) {
                table.rows[i].insertCell(cellIndex + 1).innerHTML = '&nbsp;';
            }
        }

        function deleteTableRow() {
            const cell = getSelectedCell();
            if (!cell) return;
            const table = cell.closest('table');
            table.deleteRow(cell.parentNode.rowIndex);
        }

        function deleteTableColumn() {
            const cell = getSelectedCell();
            if (!cell) return;
            const table = cell.closest('table');
            const cellIndex = cell.cellIndex;
            for (let i = 0; i < table.rows.length; i++) {
                if (table.rows[i].cells.length > cellIndex) {
                    table.rows[i].deleteCell(cellIndex);
                }
            }
        }

        function setTableHeaderRow() {
            const cell = getSelectedCell();
            if (!cell) return;
            const row = cell.parentNode;
            const isHeader = row.cells[0].tagName === 'TH';

            for (let i = 0; i < row.cells.length; i++) {
                const oldCell = row.cells[i];
                const newCell = document.createElement(isHeader ? 'td' : 'th');
                newCell.innerHTML = oldCell.innerHTML;
                newCell.style.backgroundColor = isHeader ? '' : '#F2F2F2';
                newCell.style.fontWeight = isHeader ? 'normal' : 'bold';
                row.replaceChild(newCell, oldCell);
            }
        }

        function setCellBackground(color) {
            const cell = getSelectedCell();
            if (cell) {
                cell.style.backgroundColor = color;
            }
        }

        function setRowBackground(color) {
            const cell = getSelectedCell();
            if (cell) {
                cell.parentNode.style.backgroundColor = color;
            }
        }

        // Toast notifications
        function showToast(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            document.body.appendChild(toast);

            setTimeout(() => {
                toast.remove();
            }, 4000);
        }

        // Database Management
        async function loadDatabaseOptions() {
            const select = document.getElementById('databaseSelect');
            const desc = document.getElementById('databaseDescription');

            try {
                const response = await fetch('/api/databases');
                const data = await response.json();

                select.innerHTML = '';
                for (const key in data.available) {
                    const db = data.available[key];
                    const option = document.createElement('option');
                    option.value = key;
                    option.textContent = `${db.name} ${db.exists ? '✔️' : '❌'}`;
                    if (db.active) {
                        option.selected = true;
                        desc.textContent = db.description;
                    }
                    select.appendChild(option);
                }
            } catch (error) {
                showToast('Fehler beim Laden der Datenbanken.', 'error');
            }
        }

        async function handleDatabaseChange(select) {
            const dbKey = select.value;
            const statusDiv = document.getElementById('databaseStatus');

            try {
                const response = await fetch('/api/databases/select', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ database: dbKey })
                });
                const result = await response.json();

                statusDiv.style.display = 'block';
                if (result.success) {
                    statusDiv.innerHTML = `<div class="alert alert-success">${result.message}</div>`;
                    showToast(result.message, 'success');
                } else {
                    statusDiv.innerHTML = `<div class="alert alert-error">${result.error}</div>`;
                    showToast(result.error, 'error');
                }
                loadDatabaseOptions();
            } catch (error) {
                statusDiv.style.display = 'block';
                statusDiv.innerHTML = `<div class="alert alert-error">Fehler: ${error.message}</div>`;
                showToast(`Fehler: ${error.message}`, 'error');
            }
        }

        // Phrase Management
        let currentPhrases = [];
        const langHeader = document.getElementById('resultLangHeader');

        async function searchPhrases() {
            const query = document.getElementById('searchInput').value;
            const lang = document.getElementById('searchLanguage').value;
            const mode = document.getElementById('searchMode').value;

            langHeader.textContent = document.querySelector(`#searchLanguage option[value=${lang}]`).textContent;

            try {
                const response = await fetch('/api/phrases/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ q: query, lang: lang, mode: mode })
                });
                currentPhrases = await response.json();
                renderPhrases(currentPhrases);
            } catch (error) {
                showToast(`Fehler bei der Suche: ${error}`, 'error');
            }
        }

        function renderPhrases(phrases) {
            const tableBody = document.getElementById('phrasesTable');
            tableBody.innerHTML = '';

            if (phrases.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color: var(--text-secondary);">Keine Phrasen gefunden.</td></tr>';
                return;
            }

            phrases.forEach(phrase => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${phrase.id.substring(0, 8)}...</td>
                    <td>${phrase.en_original || ''}</td>
                    <td>${phrase.translation || ''}</td>
                    <td>
                        <button onclick="showEditModal('${phrase.id}')" class="secondary" style="padding: 6px 12px;">✏️</button>
                        <button onclick="deletePhrase('${phrase.id}')" class="danger" style="padding: 6px 12px;">🗑️</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        }

        const modal = document.getElementById('phraseModal');

        function showAddModal() {
            document.getElementById('phraseForm').reset();
            document.getElementById('phraseId').value = '';
            document.getElementById('modalTitle').textContent = '✨ Neue Phrase hinzufügen';
            modal.classList.add('active');
        }

        function showAddModalWithText(text) {
            showAddModal();
            document.getElementById('enText').value = text;
        }

        async function showEditModal(id) {
            try {
                const response = await fetch(`/api/phrases/${id}/full`);
                const phrase = await response.json();

                document.getElementById('phraseId').value = phrase.id;
                document.getElementById('enText').value = phrase.en_original || '';

                for (const lang in window.appConfig.languages) {
                    document.getElementById(`${lang}Text`).value = phrase[`${lang}_original`] || '';
                }

                document.getElementById('modalTitle').textContent = '✏️ Phrase bearbeiten';
                modal.classList.add('active');

            } catch (error) {
                showToast(`Fehler beim Laden der Phrase: ${error}`, 'error');
            }
        }

        function closeModal() {
            modal.classList.remove('active');
        }

        document.getElementById('phraseForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const id = document.getElementById('phraseId').value;
            const data = {
                en_original: document.getElementById('enText').value,
            };

            for (const lang in window.appConfig.languages) {
                data[`${lang}_original`] = document.getElementById(`${lang}Text`).value;
            }

            const url = id ? `/api/phrases/${id}` : '/api/phrases';
            const method = id ? 'PUT' : 'POST';

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    showToast(result.message, 'success');
                    closeModal();
                    searchPhrases();
                } else {
                    showToast(`Fehler: ${result.error}`, 'error');
                }
            } catch (error) {
                showToast(`Fehler: ${error}`, 'error');
            }
        });

        async function deletePhrase(id) {
            if (confirm(`Soll die Phrase mit der ID ${id.substring(0,8)}... wirklich gelöscht werden?`)) {
                try {
                    const response = await fetch(`/api/phrases/${id}`, { method: 'DELETE' });
                    const result = await response.json();

                    if (response.ok) {
                        showToast(result.message, 'success');
                        searchPhrases();
                    } else {
                        showToast(`Fehler: ${result.error}`, 'error');
                    }
                } catch (error) {
                    showToast(`Fehler: ${error}`, 'error');
                }
            }
        }

        // GHS Pictograms
        let allPictograms = [];
        let selectedPictograms = [];

        async function loadGHSPictograms() {
            try {
                const response = await fetch('/api/ghs/pictograms');
                allPictograms = await response.json();
                renderGHSPictograms();
            } catch (error) {
                document.getElementById('ghsAvailableList').innerHTML = '<p style="color:var(--error)">Fehler beim Laden der Piktogramme.</p>';
            }
        }

        function renderGHSPictograms() {
            const list = document.getElementById('ghsAvailableList');
            const filter = document.getElementById('ghsFilterClass').value;
            list.innerHTML = '';

            const filtered = filter ? allPictograms.filter(p => p.hazard_class === filter) : allPictograms;

            filtered.forEach(p => {
                const isSelected = selectedPictograms.includes(p.code);
                const isDisabled = !isSelected && selectedPictograms.length >= 3;

                const item = document.createElement('div');
                item.className = `ghs-pictogram-item ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`;
                item.innerHTML = `
                    <img src="${p.svg_path}" alt="${p.name}">
                    <div class="code">${p.code}</div>
                    <div class="name">${p.name}</div>
                `;
                if (!isDisabled) {
                    item.onclick = () => toggleGHSSelection(p.code);
                }
                list.appendChild(item);
            });
        }

        function toggleGHSSelection(code) {
            const index = selectedPictograms.indexOf(code);
            if (index > -1) {
                selectedPictograms.splice(index, 1);
            } else if (selectedPictograms.length < 3) {
                selectedPictograms.push(code);
            }
            renderGHSPictograms();
            renderSelectedGHSPictograms();
        }

        function renderSelectedGHSPictograms() {
            const list = document.getElementById('ghsSelectedList');
            const webPreview = document.getElementById('ghsWebPreview');
            list.innerHTML = '';
            webPreview.innerHTML = '';
            document.getElementById('ghsSelectedCount').textContent = selectedPictograms.length;

            if (selectedPictograms.length === 0) {
                list.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">Keine Piktogramme ausgewaehlt</p>';
                return;
            }

            selectedPictograms.forEach((code, index) => {
                const pictogram = allPictograms.find(p => p.code === code);
                if (pictogram) {
                    // Main selected list
                    const item = document.createElement('div');
                    item.className = 'ghs-selected-item';
                    item.innerHTML = `
                        <button class="remove-btn" onclick="toggleGHSSelection('${code}')">&times;</button>
                        <img src="${pictogram.svg_path}" alt="${pictogram.name}">
                        <div class="position">Position ${index + 1}</div>
                    `;
                    list.appendChild(item);

                    // Web preview
                    const prevImg = document.createElement('img');
                    prevImg.src = pictogram.svg_path;
                    prevImg.style.width = '84px';
                    prevImg.style.height = '84px';
                    webPreview.appendChild(prevImg);
                }
            });
        }

        function filterGHSPictograms() {
            renderGHSPictograms();
        }

        // Stats Tab
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();

                document.getElementById('totalPhrases').textContent = data.total_phrases;

                const langStats = document.getElementById('langStats');
                langStats.innerHTML = '';

                for (const lang in data.per_language) {
                    const count = data.per_language[lang];
                    const percentage = (count / data.total_phrases * 100).toFixed(1);

                    const statBox = document.createElement('div');
                    statBox.className = 'stat-box';
                    statBox.style.textAlign = 'left';
                    statBox.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: baseline;">
                            <div class="stat-label" style="margin:0;">${lang.toUpperCase()} - {{ languages[lang] }}</div>
                            <div class="stat-value" style="font-size: 1.5em;">${count}</div>
                        </div>
                        <div class="progress-bar" style="height: 15px; margin-top: 10px;">
                            <div class="progress-fill" style="width: ${percentage}%; font-size: 0.8em; padding-right: 8px;">
                                ${percentage}%
                            </div>
                        </div>
                    `;
                    langStats.appendChild(statBox);
                }

            } catch (error) {
                showToast(`Fehler beim Laden der Statistiken: ${error}`, 'error');
            }
        }

        // Initial load
        document.addEventListener('DOMContentLoaded', () => {
            showTab('translate', document.querySelector('.tab.active'));
            loadDatabaseOptions();
            loadGHSPictograms();

            // Check for default loaded template
            const defaultLoaded = document.getElementById('fileName').textContent.includes('Standard');
            if(defaultLoaded) {
                document.getElementById('translateBtn').disabled = false;
                 // Fetch and show preview for default file
                 fetch('/api/preview/original')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('originalPreview').srcdoc = data.content;
                        document.getElementById('previewContainer').style.display = 'grid';
                    })
            }
        });


        // Bulk Correction Functions
        async function uploadBulkFile() {
            const fileInput = document.getElementById('bulkFileInput');
            const sourceLang = document.getElementById('bulkSourceLang').value;
            const statusDiv = document.getElementById('bulkStatus');

            if (!fileInput.files || !fileInput.files[0]) {
                statusDiv.innerHTML = '<div class="alert alert-error">❌ Bitte wählen Sie eine TXT-Datei aus</div>';
                return;
            }

            const file = fileInput.files[0];
            if (!file.name.endsWith('.txt')) {
                statusDiv.innerHTML = '<div class="alert alert-error">❌ Nur TXT-Dateien sind erlaubt</div>';
                return;
            }

            statusDiv.innerHTML = '<div class="alert alert-info">⏳ Wird hochgeladen...</div>';

            const formData = new FormData();
            formData.append('file', file);
            formData.append('source_lang', sourceLang);

            try {
                const response = await fetch('/api/phrases/bulk/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    statusDiv.innerHTML = `<div class="alert alert-success">
                        ✅ Erfolgreich! ${data.created} neue Phrasen erstellt, ${data.updated} Phrasen aktualisiert.
                        <br>Quellsprache: ${data.source_language.toUpperCase()}
                    </div>`;
                    // Clear file input
                    fileInput.value = '';
                    document.getElementById('bulkFileLabel').classList.remove('has-file');
                } else {
                    statusDiv.innerHTML = `<div class="alert alert-error">❌ ${data.error}</div>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="alert alert-error">❌ Fehler: ${error.message}</div>`;
            }
        }

        // File input visual feedback
        document.getElementById('bulkFileInput').addEventListener('change', function() {
            const label = document.getElementById('bulkFileLabel');
            if (this.files && this.files[0]) {
                label.classList.add('has-file');
                label.querySelector('div').textContent = '📄 ' + this.files[0].name;
            } else {
                label.classList.remove('has-file');
                label.querySelector('div').textContent = '📂 TXT-Datei auswählen';
            }
        });

        // Quick Edit function - added to fix missing function
        async function applyQuickEdit() {
            const text = document.getElementById('quickEditText').value.trim();
            const sourceLang = document.getElementById('quickSourceLang').value;
            const statusDiv = document.getElementById('bulkStatus');

            if (!text) {
                statusDiv.innerHTML = '<div class="alert alert-error">❌ Bitte geben Sie Text ein</div>';
                return;
            }

            statusDiv.innerHTML = '<div class="alert alert-info">⏳ Wird verarbeitet...</div>';

            try {
                const response = await fetch('/api/phrases/bulk/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        source_lang: sourceLang
                    })
                });

                const data = await response.json();

                if (data.success) {
                    statusDiv.innerHTML = `<div class="alert alert-success">
                        ✅ Erfolgreich! ${data.created} neue Phrasen erstellt, ${data.updated} Phrasen aktualisiert.
                        <br>Quellsprache: ${data.source_language.toUpperCase()}
                        <br>Phrase: ${data.source_phrase}
                    </div>`;
                    // Clear textarea
                    document.getElementById('quickEditText').value = '';
                } else {
                    statusDiv.innerHTML = `<div class="alert alert-error">❌ ${data.error}</div>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="alert alert-error">❌ Fehler: ${error.message}</div>`;
            }
        }

// Theme Toggle
const themeToggle = document.getElementById('themeToggle');
if (themeToggle) {
    // Check saved theme or system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;

    if (savedTheme === 'light' || (!savedTheme && prefersLight)) {
        document.body.classList.add('light-theme');
        themeToggle.textContent = '☀️';
    } else {
        themeToggle.textContent = '🌙';
    }

    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        if (document.body.classList.contains('light-theme')) {
            localStorage.setItem('theme', 'light');
            themeToggle.textContent = '☀️';
        } else {
            localStorage.setItem('theme', 'dark');
            themeToggle.textContent = '🌙';
        }
    });
}

// Sidebar Toggle
const sidebarToggle = document.getElementById('sidebarToggle');
const mainSidebar = document.getElementById('mainSidebar');
const mainGrid = document.getElementById('mainGrid');

if (sidebarToggle && mainSidebar && mainGrid) {
    sidebarToggle.addEventListener('click', () => {
        mainSidebar.classList.toggle('collapsed');
        mainGrid.classList.toggle('sidebar-collapsed');

        // Handle grid layout switch
        if (mainSidebar.classList.contains('collapsed')) {
            mainGrid.style.gridTemplateColumns = '0px 1fr';
        } else {
            mainGrid.style.gridTemplateColumns = '380px 1fr';
        }
    });
}

// Auto-save functionality
let autoSaveInterval;
const AUTO_SAVE_DELAY = 30000; // 30 seconds

function startAutoSave() {
    if (autoSaveInterval) clearInterval(autoSaveInterval);
    autoSaveInterval = setInterval(() => {
        if (isOriginalEditMode) {
            const editor = document.getElementById('originalRichTextEditor');
            if (editor && editor.innerHTML !== originalContentBeforeEdit) {
                saveChanges('original', true); // Pass true to indicate auto-save
            }
        }
        if (isEditMode) {
            const editor = document.getElementById('richTextEditor');
            if (editor && editor.innerHTML !== originalTranslatedContent) {
                saveChanges('translated', true);
            }
        }
        if (isModalOpen) {
            const editor = document.getElementById('modalRichTextEditor');
            if(editor) {
                // In modal, we can save directly to the translation file
                const newContent = editor.innerHTML;
                document.getElementById('richTextEditor').innerHTML = newContent;
                saveChanges('translated', true);
            }
        }
    }, AUTO_SAVE_DELAY);
}

function stopAutoSave() {
    if (autoSaveInterval) {
        clearInterval(autoSaveInterval);
        autoSaveInterval = null;
    }
}

// Override toggleEditMode to start/stop auto-save
const originalToggleEditMode = toggleEditMode;
toggleEditMode = function(type) {
    originalToggleEditMode(type);
    if (isOriginalEditMode || isEditMode) {
        startAutoSave();
    } else {
        stopAutoSave();
    }
};

// Override saveChanges to handle auto-save notifications differently
const originalSaveChanges = saveChanges;
saveChanges = async function(type, isAutoSave = false) {
    const isOriginal = type === 'original';
    const editor = document.getElementById(isOriginal ? 'originalRichTextEditor' : 'richTextEditor');
    const newContent = editor.innerHTML;
    const url = isOriginal ? '/api/save/original' : '/api/save/translated';

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent }),
        });
        const result = await response.json();
        if (result.success) {
            if (!isAutoSave) {
                showToast('Änderungen gespeichert!', 'success');
                document.getElementById(isOriginal ? 'originalPreview' : 'translatedPreview').srcdoc = newContent;

                // Update original content ref so subsequent discards revert to this point
                if(isOriginal) originalContentBeforeEdit = newContent;
                else originalTranslatedContent = newContent;

                toggleEditMode(type);
            } else {
                // Subtle notification for auto-save
                const toast = document.createElement('div');
                toast.className = `toast success`;
                toast.style.padding = '8px 15px';
                toast.style.fontSize = '0.85em';
                toast.style.opacity = '0.8';
                toast.textContent = 'Auto-saved...';
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 2000);
            }
        } else {
            showToast('Fehler beim Speichern: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Fehler: ' + error.message, 'error');
    }
}


// File Upload Drag and Drop
const fileInputWrappers = document.querySelectorAll('.file-input-wrapper');

fileInputWrappers.forEach(wrapper => {
    const input = wrapper.querySelector('input[type="file"]');
    const label = wrapper.querySelector('.file-input-label');

    // Highlight drop area
    ['dragenter', 'dragover'].forEach(eventName => {
        wrapper.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            label.classList.add('dragover');
        }, false);
    });

    // Remove highlight
    ['dragleave', 'drop'].forEach(eventName => {
        wrapper.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            label.classList.remove('dragover');
        }, false);
    });

    // Handle drop
    wrapper.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length) {
            input.files = files; // Assign files to input
            // Trigger the onchange event manually
            const event = new Event('change', { bubbles: true });
            input.dispatchEvent(event);
        }
    }, false);
});

// Loading Overlay Helpers
function showLoading(text = 'Bitte warten...') {
    const overlay = document.getElementById('loadingOverlay');
    const textEl = document.getElementById('loadingText');
    if (overlay && textEl) {
        textEl.textContent = text;
        overlay.classList.add('active');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// Override translateFile to use loading overlay
const originalTranslateFile = translateFile;
translateFile = async function() {
    showLoading('Übersetze Dokument... Dies kann einen Moment dauern.');
    await originalTranslateFile();
    hideLoading();
};

// Override downloadPDF to use loading overlay
const originalDownloadPDF = downloadPDF;
downloadPDF = function() {
    showLoading('Generiere PDF... Bitte warten.');
    originalDownloadPDF().finally(() => {
        hideLoading();
    });
};


// Accordion functionality for Database Tab
const accordions = document.querySelectorAll(".accordion");
accordions.forEach(acc => {
    acc.addEventListener("click", function() {
        this.classList.toggle("active");
        const panel = this.nextElementSibling;
        if (panel.style.maxHeight) {
            panel.style.maxHeight = null;
        } else {
            panel.style.maxHeight = panel.scrollHeight + "px";
        }
    });
});
