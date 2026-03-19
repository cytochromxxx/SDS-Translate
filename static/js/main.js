
        // ======================================================
        // INITIALIZATION
        // ======================================================
        document.addEventListener('DOMContentLoaded', () => {
            // ======================================================
            // THEME SWITCHER
            // ======================================================
            const themeToggle = document.getElementById('theme-toggle');
            const htmlEl = document.documentElement;

            themeToggle.addEventListener('click', () => {
                const isDark = htmlEl.classList.toggle('dark');
                htmlEl.classList.toggle('light', !isDark);
                themeToggle.textContent = isDark ? 'LIGHT' : 'DARK';
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
            });
            // Set theme from local storage
            const storedTheme = localStorage.getItem('theme');
            if (storedTheme === 'light') {
                htmlEl.classList.remove('dark');
                htmlEl.classList.add('light');
                themeToggle.textContent = 'DARK';
            } else {
                 htmlEl.classList.add('dark');
                 themeToggle.textContent = 'LIGHT';
            }

            selectFileType('html');
            showTab('translate', document.querySelector('nav button'));
            loadDatabaseOptions();
            loadGHSPictograms();
            renderSelectedGHSPictograms();
            setupDragAndDrop();

             const defaultLoaded = document.getElementById('file-label').textContent.includes('Standard');
            if(defaultLoaded) {
                document.getElementById('translateBtn').disabled = false;
                 fetch('/api/preview/original')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('originalPreview').srcdoc = data.content;
                        document.getElementById('previewContainer').style.display = 'flex';
                    })
            }

            Split(['#original-container', '#translated-container'], {
                sizes: [50, 50],
                gutterSize: 8,
                cursor: 'col-resize',
                gutterStyle: (dimension, gutterSize) => ({
                    'flex-basis': `${gutterSize}px`,
                }),
                onDrag: () => {
                    const originalIframe = document.getElementById('originalPreview');
                    const translatedIframe = document.getElementById('translatedPreview');
                    originalIframe.style.pointerEvents = 'none';
                    translatedIframe.style.pointerEvents = 'none';
                },
                onDragEnd: () => {
                    const originalIframe = document.getElementById('originalPreview');
                    const translatedIframe = document.getElementById('translatedPreview');
                    originalIframe.style.pointerEvents = 'auto';
                    translatedIframe.style.pointerEvents = 'auto';
                }
            });

            // Scroll Sync Logic
            const originalPreview = document.getElementById('originalPreview');
            const translatedPreview = document.getElementById('translatedPreview');
            const richTextEditor = document.getElementById('richTextEditor');
            const elements = [originalPreview, translatedPreview, richTextEditor];
            let isSyncing = false;

            const scrollHandler = (event) => {
                if (isSyncing) return;
                isSyncing = true;

                const scrollingElement = event.target === document ? document.scrollingElement : event.target;
                const scrollTop = scrollingElement.scrollTop;

                // Sync other elements
                if (scrollingElement.parentElement === originalPreview.contentDocument.body.parentElement) {
                    if (translatedPreview.contentDocument) translatedPreview.contentDocument.documentElement.scrollTop = scrollTop;
                    richTextEditor.scrollTop = scrollTop;
                } else if (scrollingElement.parentElement === translatedPreview.contentDocument.body.parentElement) {
                    if (originalPreview.contentDocument) originalPreview.contentDocument.documentElement.scrollTop = scrollTop;
                    richTextEditor.scrollTop = scrollTop;
                } else if (scrollingElement === richTextEditor) {
                    if (originalPreview.contentDocument) originalPreview.contentDocument.documentElement.scrollTop = scrollTop;
                    if (translatedPreview.contentDocument) translatedPreview.contentDocument.documentElement.scrollTop = scrollTop;
                }

                setTimeout(() => { isSyncing = false; }, 100);
            };

            originalPreview.addEventListener('load', () => {
                if (originalPreview.contentDocument) originalPreview.contentDocument.addEventListener('scroll', scrollHandler);
            });
            translatedPreview.addEventListener('load', () => {
                 if (translatedPreview.contentDocument) translatedPreview.contentDocument.addEventListener('scroll', scrollHandler);
            });
            richTextEditor.addEventListener('scroll', scrollHandler);

        });


        // ======================================================
        // SCRIPT CONTENT
        // ======================================================

        let currentFile = null;
        let translatedContent = null;
        let currentFileType = 'html';
        let isDirty = false;
        let autoSaveInterval;

        function showTab(tabName, btnElement) {
            document.querySelectorAll('nav button').forEach(tab => tab.classList.remove('tab-active', 'text-minerva-green'));
            if (btnElement) btnElement.classList.add('tab-active', 'text-minerva-green');
            
            document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');
            document.getElementById(tabName + '-tab').style.display = 'block';
            
            if (tabName === 'stats') loadStats();
            if (tabName === 'database') searchPhrases();
        }
        
        function selectFileType(type) {
            currentFileType = type;
            ['btnHtml', 'btnPdf', 'btnXml', 'btnCombined'].forEach(id => {
                const btn = document.getElementById(id);
                const isActive = id.toLowerCase().includes(type);
                btn.classList.toggle('bg-minerva-hover', isActive);
                btn.classList.toggle('text-minerva-green', isActive);
                btn.classList.toggle('text-light-text-secondary', !isActive);
                btn.classList.toggle('dark:text-minerva-gray', !isActive);
            });
            
            // Toggle between single and combined file upload
            const singleUpload = document.getElementById('single-file-upload');
            const combinedUpload = document.getElementById('combined-file-upload');
            
            if (type === 'combined') {
                singleUpload.classList.add('hidden');
                combinedUpload.classList.remove('hidden');
            } else {
                singleUpload.classList.remove('hidden');
                combinedUpload.classList.add('hidden');
            }
            
            document.getElementById('main-file-input').accept = `.${type}, .${type.toUpperCase()}`;
        }
        
        // Variables for combined upload
        let selectedXmlFile = null;
        let selectedPdfFile = null;
        
        function handleXmlFileSelect(input) {
            const file = input.files[0];
            if (file) {
                selectedXmlFile = file;
                document.getElementById('xml-file-label').innerHTML = `<span class="text-light-text dark:text-white font-bold">📄 ${file.name}</span>`;
                checkCombinedUploadReady();
            }
        }
        
        function handlePdfFileSelect(input) {
            const file = input.files[0];
            if (file) {
                selectedPdfFile = file;
                document.getElementById('pdf-file-label').innerHTML = `<span class="text-light-text dark:text-white font-bold">📄 ${file.name}</span>`;
                checkCombinedUploadReady();
            }
        }
        
        function checkCombinedUploadReady() {
            const btn = document.getElementById('combined-upload-btn');
            if (selectedXmlFile && selectedPdfFile) {
                btn.disabled = false;
                btn.classList.remove('opacity-50');
            } else {
                btn.disabled = true;
                btn.classList.add('opacity-50');
            }
        }
        
        async function uploadCombinedFiles() {
            if (!selectedXmlFile || !selectedPdfFile) {
                alert('Bitte sowohl eine XML- als auch eine PDF-Datei auswählen.');
                return;
            }
            
            const formData = new FormData();
            formData.append('xml_file', selectedXmlFile);
            formData.append('pdf_file', selectedPdfFile);
            
            const progressSection = document.getElementById('progressSection');
            const progressFill = document.getElementById('coverageBar');
            const progressText = document.getElementById('coverageText');
            
            progressSection.style.display = 'block';
            progressFill.style.width = '0%';
            progressText.textContent = 'Lade XML und PDF hoch...';
            
            try {
                const response = await fetch('/api/combined-import', {
                    method: 'POST',
                    body: formData
                });
                
                progressText.textContent = 'Verarbeite Daten...';
                progressFill.style.width = '50%';
                
                const result = await response.json();
                
                if (response.ok) {
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Import erfolgreich!';
                    
                    document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ <strong>${selectedXmlFile.name}</strong> und <strong>${selectedPdfFile.name}</strong> erfolgreich importiert.</div>`;
                    
                    document.getElementById('originalPreview').srcdoc = result.preview;
                    document.getElementById('previewContainer').style.display = 'flex';
                    document.getElementById('translateBtn').disabled = false;
                    document.getElementById('translatedPreview').srcdoc = '';
                    
                } else {
                    throw new Error(result.error || 'Unbekannter Fehler beim kombinierten Import');
                }
            } catch (error) {
                progressText.textContent = 'Import fehlgeschlagen!';
                document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ Fehler beim Import: ${error.message}</div>`;
            }
        }
        
        function handleFileSelect(input) {
            const file = input.files[0];
            if (file) {
                processFile(file);
            }
        }
        
        function setupDragAndDrop() {
            const dropArea = document.getElementById('file-drop-area');
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                }, false);
            });
            
            ['dragenter', 'dragover'].forEach(eventName => {
                dropArea.addEventListener(eventName, () => dropArea.classList.add('border-minerva-green'), false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                 dropArea.addEventListener(eventName, () => dropArea.classList.remove('border-minerva-green'), false);
            });

            dropArea.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt.files;
                if(files.length > 0) {
                    processFile(files[0]);
                }
            }, false);
        }

        function processFile(file) {
            document.getElementById('file-label').innerHTML = `<span class="text-light-text dark:text-white font-bold">${file.name}</span>`;
            
            const extension = file.name.split('.').pop().toLowerCase();
            if (['html', 'pdf', 'xml'].includes(extension)) {
                selectFileType(extension);
            }

            if (currentFileType === 'html') uploadFile(file);
            else if (currentFileType === 'pdf') processPdfFile(file);
            else if (currentFileType === 'xml') processXmlFile(file);
        }
        
        async function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/upload', { method: 'POST', body: formData });
                const result = await response.json();
                
                if (response.ok) {
                    document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ Datei <strong>${result.filename}</strong> geladen.</div>`;
                    currentFile = file.name;
                    document.getElementById('originalPreview').srcdoc = result.preview;
                    document.getElementById('previewContainer').style.display = 'flex';
                    document.getElementById('translateBtn').disabled = false;
                    document.getElementById('translatedPreview').srcdoc = '';
                    document.getElementById('progressSection').style.display = 'none';
                } else {
                     document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ ${result.error}</div>`;
                }
            } catch (error) {
                document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ Fehler beim Upload: ${error.message}</div>`;
            }
        }
        
       async function processGenericFile(file, endpoint) {
            const formData = new FormData();
            formData.append('file', file);

            const progressSection = document.getElementById('progressSection');
            const progressFill = document.getElementById('coverageBar');
            const progressText = document.getElementById('coverageText');
            
            progressSection.style.display = 'block';
            progressFill.style.width = '0%';
            progressText.textContent = `Lade ${currentFileType.toUpperCase()} hoch...`;

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: formData
                });
                
                progressText.textContent = `Verarbeite ${currentFileType.toUpperCase()}...`;
                progressFill.style.width = '50%';

                const result = await response.json();
                
                if (response.ok) {
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Import erfolgreich!';
                    
                    document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ <strong>${file.name}</strong> erfolgreich importiert.</div>`;
                    
                    document.getElementById('originalPreview').srcdoc = result.preview;
                    document.getElementById('previewContainer').style.display = 'flex';
                    document.getElementById('translateBtn').disabled = false;
                    document.getElementById('translatedPreview').srcdoc = '';

                } else {
                    throw new Error(result.error || `Unbekannter Fehler beim ${currentFileType.toUpperCase()}-Import`);
                }

            } catch (error) {
                progressText.textContent = 'Import fehlgeschlagen!';
                document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ Fehler beim Import: ${error.message}</div>`;
            }
        }

        function processPdfFile(file) {
            processGenericFile(file, '/api/pdf/process');
        }

        function processXmlFile(file) {
            processGenericFile(file, '/api/sdscom/process');
        }

        async function translateFile() {
            const language = document.getElementById('languageSelect').value;
            const translateBtn = document.getElementById('translateBtn');
            translateBtn.disabled = true;
            translateBtn.innerHTML = '... Übersetze ...';
            document.getElementById('progressSection').style.display = 'block';
            
            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ language, pictograms: selectedPictograms })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    document.getElementById('translatedPreview').srcdoc = `<style>body{color:black;}</style>${result.preview}`;
                    translatedContent = result.preview;
                    
                    const stats = result.stats;
                    document.getElementById('totalTexts').textContent = stats.total_texts;
                    document.getElementById('translatedCount').textContent = stats.translated_exact;
                    document.getElementById('notFoundCount').textContent = stats.not_found;
                    
                    const coverage = (stats.translated_exact / stats.total_texts * 100) || 0;
                    document.getElementById('coverageBar').style.width = `${coverage.toFixed(1)}%`;
                     document.getElementById('coverageText').textContent = `${coverage.toFixed(1)}%`;
                    
                    const notFoundList = document.getElementById('notFoundList');
                    const notFoundBadge = document.getElementById('notFoundBadge');
                    notFoundList.innerHTML = '';
                    notFoundBadge.textContent = `${result.not_found.length} UNRESOLVED`;
                    
                    if (result.not_found.length > 0) {
                        result.not_found.forEach(phrase => {
                            const item = document.createElement('div');
                            item.className = 'text-xs p-2 hover:bg-minerva-hover flex justify-between items-center';
                            item.innerHTML = `<span>${phrase.text}</span> <button onclick="showAddModalWithText('${phrase.text.replace(/'/g, "\\'")}')" class="text-minerva-green font-bold">Translate</button>`;
                            notFoundList.appendChild(item);
                        });
                    } else {
                        notFoundList.innerHTML = '<div class="text-center text-minerva-gray p-4">🎉 Alle Phrasen gefunden!</div>';
                    }
                    
                    document.getElementById('downloadNotFoundSection').style.display = 'block';
                    toggleEditor(true);
                    
                } else {
                    alert(`Übersetzungsfehler: ${result.error}`);
                }
                
            } catch (error) {
                alert(`Fehler: ${error.message}`);
            } finally {
                translateBtn.disabled = false;
                translateBtn.innerHTML = 'Übersetzung Starten';
                document.getElementById('progressSection').style.display = 'block';
            }
        }
        
        function downloadHTML() { window.location.href = '/api/download'; }
        
        function downloadPDF() {
            const btn = document.getElementById('pdfDownloadBtn');
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg> Exporting...`;

            fetch('/api/download/pdf')
                .then(response => {
                    if (response.ok) return response.blob();
                    throw new Error('PDF generation failed.');
                })
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `translated_sds.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);
                })
                .catch(error => alert(`PDF-Fehler: ${error.message}`))
                .finally(() => {
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                });
        }

        // GHS Pictograms
        let allPictograms = [];
        let selectedPictograms = [];

        function openGHSModal() { document.getElementById('ghsModal').classList.add('active'); }
        function closeGHSModal() { document.getElementById('ghsModal').classList.remove('active'); }

        async function loadGHSPictograms() {
            try {
                const response = await fetch('/api/ghs/pictograms');
                allPictograms = await response.json();
                renderGHSPictograms();
            } catch (error) {
                console.error('Fehler beim Laden der Piktogramme.');
            }
        }

        function renderGHSPictograms() {
            const list = document.getElementById('ghsAvailableList');
            if(!list) return;
            list.innerHTML = '';
            
            allPictograms.forEach(p => {
                const isSelected = selectedPictograms.includes(p.code);
                const isDisabled = !isSelected && selectedPictograms.length >= 3;
                
                const item = document.createElement('div');
                item.className = `ghs-pictogram-item border-light-border dark:border-minerva-border ${isSelected ? 'selected border-green-400' : ''} ${isDisabled ? 'disabled' : ''}`;
                item.innerHTML = `<img src="/ghs/${p.code.toLowerCase()}.png" alt="${p.name}"><div class="code text-light-text dark:text-white">${p.code}</div>`;
                if (!isDisabled) {
                    item.onclick = () => toggleGHSSelection(p.code);
                }
                list.appendChild(item);
            });
        }
        
        function toggleGHSSelection(code) {
            const index = selectedPictograms.indexOf(code);
            if (index > -1) selectedPictograms.splice(index, 1);
            else if (selectedPictograms.length < 3) selectedPictograms.push(code);
            renderGHSPictograms();
            renderSelectedGHSPictograms();
        }
        
        function renderSelectedGHSPictograms() {
            const list = document.getElementById('ghsSelectedList');
            const display = document.getElementById('ghsSelectedDisplay');
            if(!list || !display) return;
            list.innerHTML = '';
            display.innerHTML = '';
            document.getElementById('ghsSelectedCount').textContent = selectedPictograms.length;

            for(let i=0; i < 3; i++) {
                const code = selectedPictograms[i];
                const placeholder = document.createElement('div');
                placeholder.className = 'aspect-square bg-light-bg dark:bg-minerva-black border border-light-border dark:border-minerva-border rounded flex items-center justify-center hover:border-minerva-green/40 transition-colors cursor-pointer group';
                if(code) {
                    const pictogram = allPictograms.find(p => p.code === code);
                    placeholder.innerHTML = `<img src="/ghs/${pictogram.code.toLowerCase()}.png" class="p-2">`;
                     const selectedItem = placeholder.cloneNode(true);
                     selectedItem.innerHTML += `<button class="remove-btn" onclick="toggleGHSSelection('${code}')">&times;</button>`;
                    list.appendChild(selectedItem);
                } else {
                     placeholder.innerHTML = '<span class="text-lg text-light-text-secondary dark:text-minerva-gray group-hover:text-minerva-green">+</span>';
                     placeholder.onclick = openGHSModal;
                }
                display.appendChild(placeholder);
            }
        }
        
        // Database functions
        async function loadDatabaseOptions() {
            try {
                const response = await fetch('/api/databases');
                const data = await response.json();
                const select = document.getElementById('databaseSelect');
                select.innerHTML = '';
                for (const key in data.available) {
                    const db = data.available[key];
                    const option = document.createElement('option');
                    option.value = key;
                    option.textContent = db.name;
                    if (db.active) option.selected = true;
                    select.appendChild(option);
                }
            } catch (error) {
                console.error('Fehler beim Laden der Datenbanken.');
            }
        }
        
        async function handleDatabaseChange(select) {
            const dbKey = select.value;
            await fetch('/api/databases/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ database: dbKey })
            });
            loadDatabaseOptions();
        }

        async function searchPhrases(page = 1) {
            const query = document.getElementById('searchInput').value;
            const lang = document.getElementById('searchLanguage').value;
            const sortBy = document.getElementById('sortBy') ? document.getElementById('sortBy').value : 'id_desc';
            const filterEn = document.getElementById('filterEnInput') ? document.getElementById('filterEnInput').value : '';
            
            document.getElementById('resultLangHeader').textContent = lang.toUpperCase();
            const tableBody = document.getElementById('phrasesTable');

            try {
                const response = await fetch('/api/phrases/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ q: query, lang: lang, page: page, sort_by: sortBy, filter_en: filterEn })
                });
                const data = await response.json();

                if (data.error) {
                    tableBody.innerHTML = `<tr><td colspan="5" class="text-center p-4 text-red-500">${data.error}</td></tr>`;
                    return;
                }

                const phrases = data.phrases || [];
                tableBody.innerHTML = '';
                if (phrases.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="5" class="text-center p-4 text-light-text-secondary dark:text-minerva-gray">Keine Phrasen gefunden</td></tr>';
                    return;
                }
                phrases.forEach(p => {
                    const row = tableBody.insertRow();
                    row.className = "hover:bg-light-bg/50 dark:hover:bg-minerva-hover/50";
                    row.innerHTML = `
                        <td class="w-10">
                            <input type="checkbox" class="phrase-checkbox w-4 h-4 rounded border-gray-300 text-minerva-green focus:ring-minerva-green" value="${p.id}" onchange="updateBulkActions()">
                        </td>
                        <td class="text-light-text-secondary dark:text-minerva-gray">${p.id.substring(0,8)}...</td>
                        <td>${p.en_original || ''}</td>
                        <td>${p.translation || ''}</td>
                        <td class="flex gap-2">
                            <button onclick="showEditModal('${p.id}')">✏️</button>
                            <button onclick="deletePhrase('${p.id}')">🗑️</button>
                        </td>
                    `;
                });
                // Reset selection after search
                resetSelection();
                renderPagination(data.total, data.page, data.per_page);
            } catch (error) {
                tableBody.innerHTML = `<tr><td colspan="5" class="text-center p-4 text-red-500">Fehler: ${error.message}</td></tr>`;
            }
        }
        
        // Bulk selection functions
        let selectedPhraseIds = new Set();
        
        function toggleSelectAll() {
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            const checkboxes = document.querySelectorAll('.phrase-checkbox');
            
            if (selectAllCheckbox.checked) {
                checkboxes.forEach(checkbox => {
                    checkbox.checked = true;
                    selectedPhraseIds.add(checkbox.value);
                });
            } else {
                checkboxes.forEach(checkbox => {
                    checkbox.checked = false;
                    selectedPhraseIds.delete(checkbox.value);
                });
            }
            updateBulkActions();
        }
        
        function updateBulkActions() {
            const checkboxes = document.querySelectorAll('.phrase-checkbox');
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            
            // Update selected set
            selectedPhraseIds.clear();
            checkboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    selectedPhraseIds.add(checkbox.value);
                }
            });
            
            // Update select all checkbox state
            if (checkboxes.length > 0 && selectedPhraseIds.size === checkboxes.length) {
                selectAllCheckbox.checked = true;
                selectAllCheckbox.indeterminate = false;
            } else if (selectedPhraseIds.size > 0) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = true;
            } else {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            }
            
            // Show/hide bulk actions
            const bulkActions = document.getElementById('bulkActions');
            const selectedCount = document.getElementById('selectedCount');
            
            if (selectedPhraseIds.size > 0) {
                bulkActions.style.display = 'flex';
                selectedCount.textContent = `${selectedPhraseIds.size} ausgewählt`;
            } else {
                bulkActions.style.display = 'none';
            }
        }
        
        function resetSelection() {
            selectedPhraseIds.clear();
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            }
            const bulkActions = document.getElementById('bulkActions');
            if (bulkActions) {
                bulkActions.style.display = 'none';
            }
        }
        
        async function bulkDeleteSelected() {
            const ids = Array.from(selectedPhraseIds);
            if (ids.length === 0) return;
            
            const confirmed = confirm(`Möchten Sie wirklich ${ids.length} Phrase(n) löschen?\n\nDiese Aktion kann nicht rückgängig gemacht werden.`);
            
            if (!confirmed) return;
            
            try {
                const response = await fetch('/api/phrases/bulk/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: ids })
                });
                const data = await response.json();
                
                if (data.success) {
                    alert(`${data.deleted_count} Phrase(n) erfolgreich gelöscht.`);
                    searchPhrases(); // Reload the table
                } else {
                    alert(`Fehler: ${data.error}`);
                }
            } catch (error) {
                alert(`Fehler: ${error.message}`);
            }
        }
        
        async function exportPhrases(format) {
            // Get selected IDs or empty array for all
            const ids = Array.from(selectedPhraseIds);
            const lang = document.getElementById('searchLanguage').value;
            
            // Confirm if exporting all (no selection)
            if (ids.length === 0) {
                if (!confirm('Keine Phrasen ausgewählt. Möchten Sie ALLE Phrasen exportieren?')) {
                    return;
                }
            }
            
            try {
                const response = await fetch('/api/phrases/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        ids: ids,
                        format: format,
                        lang: lang
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    alert(`Export-Fehler: ${errorData.error || 'Unbekannter Fehler'}`);
                    return;
                }
                
                // Handle the blob response
                const blob = await response.blob();
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = `translations_export.${format}`;
                
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename=([^;]+)/);
                    if (match) filename = match[1];
                }
                
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
            } catch (error) {
                alert(`Export-Fehler: ${error.message}`);
            }
        }

        function renderPagination(total, page, per_page) {
            const paginationContainer = document.getElementById('pagination-container');
            paginationContainer.innerHTML = '';
            const totalPages = Math.ceil(total / per_page);

            for(let i = 1; i <= totalPages; i++) {
                const button = document.createElement('button');
                button.textContent = i;
                button.className = `px-3 py-1 rounded mx-1 ${i === page ? 'bg-minerva-green text-white' : 'bg-light-bg dark:bg-minerva-black'}`;
                button.onclick = () => searchPhrases(i);
                paginationContainer.appendChild(button);
            }
        }

        let modal;
        function showAddModal() {
            if (!modal) modal = document.getElementById('phraseModal');
            document.getElementById('phraseForm').reset();
            document.getElementById('phraseId').value = '';
            document.getElementById('modalTitle').textContent = 'Neue Phrase hinzufügen';
            modal.classList.add('active');
            isDirty = false;
        }
        function showAddModalWithText(text) {
            showAddModal();
            document.getElementById('enText').value = text;
        }

        async function showEditModal(id) {
            if (!modal) modal = document.getElementById('phraseModal');
            const response = await fetch(`/api/phrases/${id}/full`);
            const phrase = await response.json();
            document.getElementById('phraseId').value = phrase.id;
            document.getElementById('enText').value = phrase.en_original || '';
            document.querySelectorAll('[id$="Text"]').forEach(el => {
                const lang = el.id.replace('Text', '');
                if (lang !== 'en') el.value = phrase[`${lang}_original`] || '';
            });
            document.getElementById('modalTitle').textContent = 'Phrase bearbeiten';
            modal.classList.add('active');
            isDirty = false;
        }
        function closeModal() {
            if (!modal) modal = document.getElementById('phraseModal');
            if(isDirty) {
                if(confirm("You have unsaved changes. Are you sure you want to close?")) {
                    modal.classList.remove('active');
                }
            } else {
                modal.classList.remove('active');
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            modal = document.getElementById('phraseModal');
            document.getElementById('phraseForm').addEventListener('input', () => { isDirty = true; });
            document.getElementById('phraseForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                isDirty = false;
                const id = document.getElementById('phraseId').value;
                const data = { en_original: document.getElementById('enText').value };
                document.querySelectorAll('[id$="Text"]').forEach(el => {
                    const lang = el.id.replace('Text', '');
                    data[`${lang}_original`] = el.value;
                });
                const url = id ? `/api/phrases/${id}` : '/api/phrases';
                const method = id ? 'PUT' : 'POST';
                await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                closeModal();
                searchPhrases();
            });
        });

        async function uploadBulkFile() {
            const fileInput = document.getElementById('bulkFileInput');
            const sourceLang = document.getElementById('bulkSourceLang').value;
            const statusDiv = document.getElementById('bulkStatus');

            if (!fileInput.files || !fileInput.files[0]) {
                statusDiv.innerHTML = '<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">Bitte eine TXT-Datei auswaehlen</div>';
                return;
            }

            statusDiv.innerHTML = '<div class="text-blue-400 text-xs p-2 bg-blue-500/10 rounded">Wird hochgeladen...</div>';

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('source_lang', sourceLang);

            try {
                const response = await fetch('/api/phrases/bulk/upload', { method: 'POST', body: formData });
                const data = await response.json();
                if (data.success) {
                    statusDiv.innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">&#10003; ${data.created} neue Phrasen erstellt, ${data.updated} aktualisiert (Sprache: ${data.source_language.toUpperCase()})</div>`;
                    fileInput.value = '';
                } else {
                    statusDiv.innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">${data.error}</div>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">Fehler: ${error.message}</div>`;
            }
        }

        async function applyQuickEdit() {
            const text = document.getElementById('quickEditText').value.trim();
            const sourceLang = document.getElementById('quickSourceLang').value;
            const statusDiv = document.getElementById('bulkStatus');

            if (!text) {
                statusDiv.innerHTML = '<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">Bitte Text eingeben</div>';
                return;
            }

            statusDiv.innerHTML = '<div class="text-blue-400 text-xs p-2 bg-blue-500/10 rounded">Wird verarbeitet...</div>';

            try {
                const response = await fetch('/api/phrases/bulk/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, source_lang: sourceLang })
                });
                const data = await response.json();
                if (data.success) {
                    statusDiv.innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">&#10003; ${data.created} neue Phrasen erstellt, ${data.updated} aktualisiert (Sprache: ${data.source_language.toUpperCase()})</div>`;
                    document.getElementById('quickEditText').value = '';
                } else {
                    statusDiv.innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">${data.error}</div>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">Fehler: ${error.message}</div>`;
            }
        }

        async function deletePhrase(id) {
            if (confirm(`Diese Phrase wirklich löschen?`)) {
                await fetch(`/api/phrases/${id}`, { method: 'DELETE' });
                searchPhrases();
            }
        }
        
        // Export document functions
        async function exportDocument(format) {
            const exportBtn = event.target.closest('button');
            const originalText = exportBtn.innerHTML;
            
            // Show loading indicator
            exportBtn.innerHTML = '⏳ Exportiere...';
            exportBtn.disabled = true;
            
            try {
                const response = await fetch('/api/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ format: format })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    alert(`Export-Fehler: ${errorData.error || 'Unbekannter Fehler'}`);
                    return;
                }
                
                // Handle the blob response
                const blob = await response.blob();
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = `translated_document.${format}`;
                
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename=([^;]+)/);
                    if (match) filename = match[1];
                }
                
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
            } catch (error) {
                alert(`Export-Fehler: ${error.message}`);
            } finally {
                // Restore button
                exportBtn.innerHTML = originalText;
                exportBtn.disabled = false;
            }
        }
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('dbStats').innerHTML = `
                    <div class="bg-light-bg dark:bg-minerva-card p-4 rounded-lg"><div class="text-3xl font-bold">${data.total_phrases}</div><div class="text-sm text-light-text-secondary dark:text-minerva-gray">Gesamtphrasen</div></div>
                `;

                const langStatsContainer = document.getElementById('langStats');
                langStatsContainer.innerHTML = '';
                Object.entries(data.per_language).forEach(([lang, count]) => {
                    const percentage = (count / data.total_phrases * 100).toFixed(1);
                    langStatsContainer.innerHTML += `
                        <div class="bg-light-bg dark:bg-minerva-card p-4 rounded-lg">
                            <div class="flex justify-between items-baseline">
                                <div class="font-bold text-lg">${lang.toUpperCase()}</div>
                                <div class="text-xl">${count}</div>
                            </div>
                            <div class="w-full bg-light-border dark:bg-minerva-border rounded-full h-2.5 mt-2">
                                <div class="bg-minerva-green h-2.5 rounded-full" style="width: ${percentage}%"></div>
                            </div>
                        </div>
                    `;
                });
            } catch (e) {
                console.error(e)
            }
        }
        
        function toggleEditor(show) {
            const editor = document.getElementById('richTextEditor');
            const originalEditor = document.getElementById('originalEditor');
            const translatedIframe = document.getElementById('translatedPreview');
            const originalIframe = document.getElementById('originalPreview');
            const toolbar = document.getElementById('editor-toolbar');
            const editBtn = document.getElementById('editBtn');
            
            if (show) {
                // Load content into editors
                const originalContent = originalIframe.srcdoc;
                const translatedContent = translatedIframe.srcdoc;
                
                // Add editing CSS to make content fully editable
                const editingCSS = `
                    <style>
                        * { pointer-events: auto !important; }
                        body { pointer-events: auto !important; }
                        .page { pointer-events: auto !important; }
                        [contenteditable] { pointer-events: auto !important; }
                        [contenteditable]:hover { outline: 1px dashed #76B82A; }
                        table { border-collapse: collapse; width: 100%; }
                        th, td { border: 1px solid #000; padding: 3px 5px; }
                    </style>
                `;
                
                // Inject CSS into content
                const processContent = (content) => {
                    if (content && content.includes('</head>')) {
                        return content.replace('</head>', editingCSS + '</head>');
                    } else if (content && content.includes('<html>')) {
                        return '<html><head>' + editingCSS + '</head><body>' + content.replace(/<html>|<\/html>|<body>|<\/body>/g, '') + '</body></html>';
                    }
                    return content;
                };
                
                originalEditor.innerHTML = processContent(originalContent);
                editor.innerHTML = processContent(translatedContent);
                
                // Show editors, hide iframes
                translatedIframe.style.display = 'none';
                originalIframe.style.display = 'none';
                editor.style.display = 'block';
                originalEditor.style.display = 'block';
                
                // Show toolbar
                toolbar.style.display = 'flex';
                
                // Update button text
                editBtn.textContent = '(Beenden)';
                
                startAutoSave();
            } else {
                // Save content back to iframes
                translatedIframe.srcdoc = editor.innerHTML;
                originalIframe.srcdoc = originalEditor.innerHTML;
                
                // Show iframes, hide editors
                translatedIframe.style.display = 'block';
                originalIframe.style.display = 'block';
                editor.style.display = 'none';
                originalEditor.style.display = 'none';
                
                // Hide toolbar
                toolbar.style.display = 'none';
                
                // Update button text
                editBtn.textContent = '(Bearbeiten)';
                
                stopAutoSave();
            }
        }

        function startAutoSave() {
            if (autoSaveInterval) clearInterval(autoSaveInterval);
            autoSaveInterval = setInterval(autoSaveChanges, 30000);
        }

        function stopAutoSave() {
            clearInterval(autoSaveInterval);
        }

        async function autoSaveChanges() {
            const editor = document.getElementById('richTextEditor');
            const content = editor.innerHTML;
            showSaveStatus('Saving...');
            try {
                const response = await fetch('/api/save/translated', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: content })
                });
                const result = await response.json();
                if(result.success) {
                    showSaveStatus('Saved!');
                } else {
                    showSaveStatus('Error saving!');
                }
            } catch (error) {
                showSaveStatus('Error saving!');
            }
        }

        // Table editing functions
        function insertTable() {
            const table = document.createElement('table');
            const tbody = document.createElement('tbody');
            for (let i = 0; i < 3; i++) {
                const row = document.createElement('tr');
                for (let j = 0; j < 3; j++) {
                    const cell = document.createElement(i === 0 ? 'th' : 'td');
                    cell.textContent = i === 0 ? `Header ${j+1}` : `Cell ${i},${j}`;
                    row.appendChild(cell);
                }
                tbody.appendChild(row);
            }
            table.appendChild(tbody);
            table.style.border = '1px solid #000';
            table.style.borderCollapse = 'collapse';
            table.style.width = '100%';
            table.querySelectorAll('th, td').forEach(cell => {
                cell.style.border = '1px solid #000';
                cell.style.padding = '3px 5px';
            });
            document.execCommand('insertHTML', false, table.outerHTML);
        }

        function insertRow() {
            const selection = window.getSelection();
            const table = findParent(selection.anchorNode, 'TABLE');
            if (table) {
                const row = document.createElement('tr');
                const cellCount = table.querySelector('tr').children.length;
                for (let i = 0; i < cellCount; i++) {
                    const cell = document.createElement('td');
                    cell.textContent = 'New Cell';
                    cell.style.border = '1px solid #000';
                    cell.style.padding = '3px 5px';
                    row.appendChild(cell);
                }
                const currentRow = findParent(selection.anchorNode, 'TR');
                if (currentRow) {
                    currentRow.parentNode.insertBefore(row, currentRow.nextSibling);
                } else {
                    table.querySelector('tbody').appendChild(row);
                }
            }
        }

        function insertColumn() {
            const selection = window.getSelection();
            const table = findParent(selection.anchorNode, 'TABLE');
            if (table) {
                table.querySelectorAll('tr').forEach((row, rowIndex) => {
                    const cell = document.createElement(rowIndex === 0 ? 'th' : 'td');
                    cell.textContent = rowIndex === 0 ? 'New Header' : 'New Cell';
                    cell.style.border = '1px solid #000';
                    cell.style.padding = '3px 5px';
                    const currentCell = findParent(selection.anchorNode, 'TH, TD');
                    if (currentCell) {
                        const cellIndex = Array.from(row.children).indexOf(currentCell);
                        if (cellIndex >= 0) {
                            row.insertBefore(cell, currentCell.nextSibling);
                        } else {
                            row.appendChild(cell);
                        }
                    } else {
                        row.appendChild(cell);
                    }
                });
            }
        }

        function deleteRow() {
            const selection = window.getSelection();
            const row = findParent(selection.anchorNode, 'TR');
            if (row && row.parentNode.children.length > 1) {
                row.parentNode.removeChild(row);
            }
        }

        function deleteColumn() {
            const selection = window.getSelection();
            const cell = findParent(selection.anchorNode, 'TH, TD');
            if (cell) {
                const table = findParent(selection.anchorNode, 'TABLE');
                const row = findParent(selection.anchorNode, 'TR');
                const cellIndex = Array.from(row.children).indexOf(cell);
                if (row.children.length > 1) {
                    table.querySelectorAll('tr').forEach(row => {
                        if (row.children[cellIndex]) {
                            row.removeChild(row.children[cellIndex]);
                        }
                    });
                }
            }
        }

        function deleteTable() {
            const selection = window.getSelection();
            const table = findParent(selection.anchorNode, 'TABLE');
            if (table) {
                table.parentNode.removeChild(table);
            }
        }

        function changeTableCellBgColor(color) {
            const selection = window.getSelection();
            const cell = findParent(selection.anchorNode, 'TH, TD');
            if (cell) {
                cell.style.backgroundColor = color;
            }
        }

        function changeTableCellBorderColor(color) {
            const selection = window.getSelection();
            const cell = findParent(selection.anchorNode, 'TH, TD');
            if (cell) {
                cell.style.borderColor = color;
            }
        }

        function findParent(node, tagName) {
            while (node && node.nodeType === Node.ELEMENT_NODE) {
                if (node.tagName === tagName) {
                    return node;
                }
                node = node.parentNode;
            }
            return null;
        }

        function showSaveStatus(message) {
            const statusEl = document.getElementById('saveStatus');
            statusEl.textContent = message;
            setTimeout(() => {
                statusEl.textContent = '';
            }, 3000);
        }

    