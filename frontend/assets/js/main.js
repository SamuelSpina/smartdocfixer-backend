// Main JavaScript Logic for SmartDocFixer Landing Page

document.addEventListener('DOMContentLoaded', () => {
            
    // --- CONFIGURATION ---
    const API_URL = "https://smartdocfixer-api.onrender.com"; // Use your local server for testing, then change to live URL

    // --- DOM ELEMENT REFERENCES ---
    const homeView = document.getElementById('view-home');
    const previewView = document.getElementById('view-preview');
    
    const uploader = document.getElementById('uploader');
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const fileNameEl = document.getElementById('file-name');
    const removeFileBtn = document.getElementById('remove-file');
    const submitBtn = document.getElementById('submit-btn');
    const homeMessageArea = document.getElementById('home-message-area');

    const correctedTextPreview = document.getElementById('corrected-text-preview');
    const downloadBasicBtn = document.getElementById('download-basic-btn');
    const previewMessageArea = document.getElementById('preview-message-area');

    const pricingLink = document.getElementById('pricingLink');
    const signInLink = document.getElementById('signInLink');
    const getStartedLink = document.getElementById('getStartedLink');
    const accountInfo = document.getElementById('accountInfo');
    const userEmailEl = document.getElementById('userEmail');
    const logoutBtn = document.getElementById('logoutBtn');
    const upgradeBtn = document.getElementById('upgradeBtn');

    // --- Interactive Demo Elements ---
    const beforeBtn = document.getElementById('before-btn');
    const afterBtn = document.getElementById('after-btn');
    const beforeContent = document.getElementById('before-content');
    const afterContent = document.getElementById('after-content');

    // --- STATE MANAGEMENT ---
    let currentFile = null;

    // --- CORE FUNCTIONS ---
    function showView(viewName) {
        if (homeView) homeView.classList.add('hidden');
        if (previewView) previewView.classList.add('hidden');
        
        const view = document.getElementById(`view-${viewName}`);
        if (view) {
            view.classList.remove('hidden');
        }
        window.scrollTo(0, 0);
    }

    function showMessage(area, msg, type = 'info') {
        const el = area === 'home' ? homeMessageArea : previewMessageArea;
        el.textContent = msg;
        if (type === 'error') el.className = 'mt-4 text-sm text-red-400';
        else if (type === 'success') el.className = 'mt-4 text-sm text-green-400';
        else el.className = 'mt-4 text-sm text-gray-400';
    }

    // --- UPLOADER LOGIC (only runs if uploader exists) ---
    if (uploadArea) {
        uploadArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => handleFileSelect(e.target));
        removeFileBtn.addEventListener('click', clearFile);
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        uploadArea.addEventListener('dragenter', () => uploadArea.classList.add('bg-brand-light-slate'));
        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('bg-brand-light-slate'));
        uploadArea.addEventListener('drop', (e) => {
            uploadArea.classList.remove('bg-brand-light-slate');
            handleFileSelect(e.dataTransfer);
        });
    }

    function handleFileSelect(input) {
        const file = input.files[0];
        if (file && file.name.endsWith('.docx')) {
            currentFile = file;
            updateUploaderUI();
        } else {
            clearFile();
            if (homeMessageArea) showMessage('home', 'Please select a valid .docx file.', 'error');
        }
    }

    function updateUploaderUI() {
        if (currentFile) {
            fileNameEl.textContent = currentFile.name;
            fileInfo.classList.remove('hidden');
            uploadArea.classList.add('hidden');
        } else {
            fileInfo.classList.add('hidden');
            uploadArea.classList.remove('hidden');
            fileInput.value = '';
        }
    }

    function clearFile() {
        currentFile = null;
        updateUploaderUI();
        if (homeMessageArea) showMessage('home', '');
    }

    // --- MAIN SUBMIT LOGIC ---
    if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
            if (!currentFile) {
                showMessage('home', 'Please select a file first.', 'error');
                return;
            }
    
            const token = localStorage.getItem('userToken');
            if (!token) {
                window.location.href = 'signup.html';
                return;
            }
    
            showMessage('home', 'Uploading and processing...', 'info');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Working...';
    
            const formData = new FormData();
            formData.append('file', currentFile);
    
            try {
                const response = await fetch(`${API_URL}/fix-document/`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });
    
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    // The backend suggests a filename, but we can construct one too
                    const contentDisposition = response.headers.get('content-disposition');
                    let filename = `SmartDocFixed_${currentFile.name}`;
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                        if (filenameMatch.length > 1) {
                            filename = filenameMatch[1];
                        }
                    }
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    a.remove();
                    showMessage('home', 'Your document has been downloaded!', 'success');
                } else {
                    const errorData = await response.json();
                    if (response.status === 402) { // Payment Required
                         showMessage('home', errorData.detail.message || 'Upgrade to Pro to continue.', 'error');
                    } else {
                        showMessage('home', errorData.detail || 'An error occurred.', 'error');
                    }
                }
            } catch (error) {
                console.error('Error fixing document:', error);
                showMessage('home', 'Could not connect to the server.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Fix My Document';
                clearFile();
            }
        });
    }

    // --- AUTH STATE MANAGEMENT ---
    function updateAuthState() {
        const token = localStorage.getItem('userToken');
        const email = localStorage.getItem('userEmail');
        const plan = localStorage.getItem('userPlan'); // 'free' or 'pro'

        if (token && email) {
            // --- Logged-in state ---
            if (pricingLink) pricingLink.classList.add('hidden');
            if (signInLink) signInLink.classList.add('hidden');
            if (getStartedLink) getStartedLink.classList.add('hidden');
            
            if (accountInfo) {
                accountInfo.classList.remove('hidden');
                accountInfo.classList.add('md:flex');
            }
            if (userEmailEl) userEmailEl.textContent = email;

            if (plan === 'free' && upgradeBtn) {
                upgradeBtn.classList.remove('hidden');
            } else if (upgradeBtn) {
                upgradeBtn.classList.add('hidden');
            }

            // Redirect pro users away from the plan selection page
            if (plan === 'pro' && window.location.pathname.endsWith('choose-plan.html')) {
                window.location.href = 'dashboard.html';
            }

        } else {
            // --- Logged-out state ---
            if (pricingLink) pricingLink.classList.remove('hidden');
            if (signInLink) signInLink.classList.remove('hidden');
            if (getStartedLink) getStartedLink.classList.remove('hidden');

            if (accountInfo) {
                accountInfo.classList.add('hidden');
                accountInfo.classList.remove('md:flex');
            }
            if (userEmailEl) userEmailEl.textContent = '';
            if (upgradeBtn) upgradeBtn.classList.add('hidden');
        }
    }
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            localStorage.removeItem('userToken');
            localStorage.removeItem('userEmail');
            localStorage.removeItem('userPlan'); // Clear plan on logout
            updateAuthState();
            window.location.href = 'login.html'; // Redirect to login page on logout
        });
    }

    // --- Interactive Demo Logic (Simplified & Corrected) ---
    function setDemoState(isAfter) {
        if (isAfter) {
            // Update button styles
            afterBtn.classList.add('active');
            beforeBtn.classList.remove('active');

            // Update content visibility
            beforeContent.classList.remove('is-active');
            afterContent.classList.add('is-active');

        } else {
            // Update button styles
            beforeBtn.classList.add('active');
            afterBtn.classList.remove('active');
            
            // Update content visibility
            afterContent.classList.remove('is-active');
            beforeContent.classList.add('is-active');
        }
    }

    if (beforeBtn && afterBtn) {
        beforeBtn.addEventListener('click', () => setDemoState(false));
        afterBtn.addEventListener('click', () => setDemoState(true));
    }

    // --- Testimonial Marquee Logic ---
    function setupMarquee() {
        const marquee = document.querySelector('.testimonial-marquee');
        if (marquee) {
            const cards = Array.from(marquee.children);
            cards.forEach(card => {
                const clone = card.cloneNode(true);
                marquee.appendChild(clone);
            });
        }
    }

    // --- FAQ Accordion Logic ---
    function setupAccordion() {
        const faqItems = document.querySelectorAll('.faq-item');
        faqItems.forEach(item => {
            const question = item.querySelector('.faq-question');
            question.addEventListener('click', () => {
                const currentlyActive = document.querySelector('.faq-item.active');
                if (currentlyActive && currentlyActive !== item) {
                    currentlyActive.classList.remove('active');
                }
                item.classList.toggle('active');
            });
        });
    }

    // --- INITIALIZATION ---
    updateAuthState();
    if (beforeContent) setDemoState(false); // Set the initial state to "Before"
    setupMarquee();
    setupAccordion();
});