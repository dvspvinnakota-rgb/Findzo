/* ==========================================================================
   Findzo - Interactive Frontend Application Script
   ========================================================================== */

const firebaseConfig = {
  apiKey: "AIzaSyCuAEXOw7giFvXdzovW5rOgNlJvawq8hFo",
  authDomain: "findzo-4599e.firebaseapp.com",
  projectId: "findzo-4599e",
  storageBucket: "findzo-4599e.firebasestorage.app",
  messagingSenderId: "224485628869",
  appId: "1:224485628869:web:a873a54789422a813a09ac",
  measurementId: "G-V38ZXTMK6F"
};

const firebaseApp = firebase.apps.length ? firebase.apps[0] : firebase.initializeApp(firebaseConfig);
const firebaseDb = firebase.firestore ? firebase.firestore() : null;
const firebaseAnalytics = firebase.analytics ? firebase.analytics() : null;
window.firebaseApp = firebaseApp;
window.firebaseDb = firebaseDb;
window.firebaseAnalytics = firebaseAnalytics;

// Application State
const state = {
  user: {
    isAuthenticated: false,
    mobile: "9876543210",
    role: "seeker",
    name: "Worker / Job Seeker",
    location: "Andheri West, Mumbai",
    pincode: "400058"
  },
  savedJobIds: [],
  activeCategory: "all",
  activeFilterTag: "all",
  activeQuickFilter: "all",
  activeMealService: "all",
  activeKeyword: "",
  allJobs: [],
  selectedJobForApply: null,
  currentLanguage: "en"
};

// Language Dictionary (Multi-language Support Ready)
const translations = {
  en: {
    workNear: "Work Near:",
    searchPlaceholder: "Search catering, event crew, waiter, pincode...",
    dailyPay: "Paid Daily",
    sameDay: "Same-Day Start",
    toolsProvided: "Tools Provided",
    applyBtn: "One-Tap Call / Apply"
  },
  hi: {
    workNear: "काम का क्षेत्र:",
    searchPlaceholder: "कैटरिंग, इवेंट स्टाफ, वेटर, पिनकोड खोजें...",
    dailyPay: "दैनिक वेतन",
    sameDay: "आज ही शुरू करें",
    toolsProvided: "औजार दिए जाएंगे",
    applyBtn: "कॉल करें / आवेदन करें"
  },
  mr: {
    workNear: "कामाचे ठिकाण:",
    searchPlaceholder: "केटरिंग, इव्हेंट स्टाफ, वेटर, पिनकोड शोधा...",
    dailyPay: "रोजचा पगार",
    sameDay: "आजच सुरू करा",
    toolsProvided: "साधने दिली जातील",
    applyBtn: "कॉल्स करा / अर्ज करा"
  },
  te: {
    workNear: "పని ప్రాంతం:",
    searchPlaceholder: "కేటరింగ్, ఈవెంట్ సిబ్బంది, వెయిటర్, పిన్‌కోడ్ వెతకండి...",
    dailyPay: "రోజువారీ జీతం",
    sameDay: "ఈ రోజే ప్రారంభం",
    toolsProvided: "పరికరాలు లభిస్తాయి",
    applyBtn: "కాల్ చేయండి / దరఖాస్తు చేయండి"
  }
};

// Initialize Application on Page Load
document.addEventListener("DOMContentLoaded", () => {
  loadCategories();
  loadJobs();

  // Close modal when clicking outside modal box
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        closeModal(overlay.id);
      }
    });
  });

  // Check saved state from localStorage
  const localSaved = localStorage.getItem("findzo_saved_jobs");
  if (localSaved) {
    state.savedJobIds = JSON.parse(localSaved);
    updateSavedCountBadge();
  }

  const localUser = localStorage.getItem("findzo_user");
  if (localUser) {
    state.user = JSON.parse(localUser);
    updateUserNavDisplay();
  }
});

// ==========================================
// API DATA FETCHING & RENDERING
// ==========================================

async function loadCategories() {
  try {
    const response = await fetch("/api/categories");
    const categories = await response.json();
    renderCategoryGrid(categories);
  } catch (err) {
    console.error("Failed to load categories:", err);
  }
}

function renderCategoryGrid(categories) {
  const container = document.getElementById("category-cards-container");
  if (!container) return;

  container.innerHTML = categories.map(cat => {
    let imgHtml = "";
    if (cat.image) {
      imgHtml = `<div class="category-img-box"><img src="${cat.image}" alt="${cat.name}"></div>`;
    } else {
      imgHtml = `<div class="category-img-box"><i class="fa-solid fa-briefcase category-icon-fallback"></i></div>`;
    }

    const isActive = state.activeCategory === cat.id ? "active" : "";

    return `
      <div class="category-card ${isActive}" onclick="filterByCategory('${cat.id}')">
        ${imgHtml}
        <div class="category-name">${cat.name}</div>
        <div class="category-count">${cat.count} Openings</div>
      </div>
    `;
  }).join("");
}

async function loadJobs() {
  try {
    if (window.firebaseDb) {
      const snapshot = await window.firebaseDb.collection("jobs").limit(20).get();
      if (!snapshot.empty) {
        const firebaseJobs = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
        state.allJobs = firebaseJobs;
        renderJobSections(firebaseJobs);
        renderRecentActivity(firebaseJobs);
        return;
      }
    }
  } catch (err) {
    console.warn("Firebase jobs unavailable, falling back to local API:", err);
  }

  try {
    let url = `/api/jobs?`;
    if (state.activeCategory && state.activeCategory !== "all") {
      url += `category=${encodeURIComponent(state.activeCategory)}&`;
    }
    if (state.activeKeyword) {
      url += `keyword=${encodeURIComponent(state.activeKeyword)}&`;
    }
    if (state.activeFilterTag && state.activeFilterTag !== "all") {
      url += `fast_tag=${encodeURIComponent(state.activeFilterTag)}&`;
    }
    if (state.activeQuickFilter === "today") {
      url += "today=true&";
    } else if (state.activeQuickFilter === "near_me") {
      const pincode = state.user.pincode;
      const location = state.user.location;
      url += pincode
        ? `pincode=${encodeURIComponent(pincode)}&`
        : `location=${encodeURIComponent(location)}&`;
    }
    if (state.activeMealService !== "all") {
      url += `meal_service=${encodeURIComponent(state.activeMealService)}&`;
    }

    const response = await fetch(url);
    const data = await response.json();
    state.allJobs = data.jobs;

    renderJobSections(data.jobs);
    renderRecentActivity(data.jobs);
  } catch (err) {
    console.error("Failed to fetch jobs:", err);
  }
}

function renderJobSections(jobs) {
  const cateringGrid = document.getElementById("catering-jobs-grid");
  const cateringJobs = jobs.filter(j => j.category === "catering");
  if (cateringGrid) cateringGrid.innerHTML = renderCardsList(cateringJobs.slice(0, 6));
}

function renderCardsList(jobsList) {
  if (!jobsList || jobsList.length === 0) {
    return `
      <div style="grid-column: 1 / -1; padding: 30px; text-align: center; color: var(--text-muted); background: rgba(255,255,255,0.03); border-radius: var(--radius-md);">
        <i class="fa-solid fa-folder-open" style="font-size: 2rem; margin-bottom: 10px; color: var(--accent-gold);"></i>
        <p>No matching local jobs found for current filter criteria.</p>
      </div>
    `;
  }

  return jobsList.map(job => {
    const isSaved = state.savedJobIds.includes(job.id);
    const bookmarkClass = isSaved ? "saved fa-solid" : "fa-regular";

    let eventBadge = "";
    if (job.event_date) {
      eventBadge = `<span class="tag-badge event"><i class="fa-solid fa-calendar-star"></i> ${job.event_date}</span>`;
    }

    let tagsHtml = job.tags.map(t => {
      let extra = t === "Paid Daily" ? "style='color: var(--accent-emerald); font-weight:700;'" : "";
      return `<span class="tag-badge" ${extra}>${t}</span>`;
    }).join("");
    const mealServiceLabels = {
      lunch: "Lunch",
      dinner: "Dinner",
      "breakfast+lunch+dinner": "Breakfast + Lunch + Dinner",
      "lunch+dinner": "Lunch + Dinner"
    };
    const mealServicesHtml = (job.meal_services || [])
      .map(service => `<span class="tag-badge">${mealServiceLabels[service] || service}</span>`)
      .join("");

    return `
      <div class="job-card">
        <div>
          <div class="job-card-header">
            <div>
              <h3 class="job-title">${job.title}</h3>
              <div class="employer-info">
                <span>${job.employer_name}</span>
                <span class="verified-badge"><i class="fa-solid fa-circle-check"></i> ${job.employer_rating}★</span>
              </div>
            </div>
            <button class="job-bookmark-btn ${isSaved ? 'saved' : ''}" onclick="toggleSaveJob('${job.id}')">
              <i class="${bookmarkClass} fa-bookmark"></i>
            </button>
          </div>

          <div class="pay-rate-box">
            <span class="pay-amount">${job.rate_formatted}</span>
            <span class="pay-type">${job.rate_type} Payout</span>
          </div>

          <div class="job-meta-grid">
            <div class="meta-item">
              <i class="fa-solid fa-location-dot meta-icon"></i> ${job.location}
            </div>
            <div class="meta-item">
              <i class="fa-solid fa-route meta-icon"></i> ${job.distance}
            </div>
            <div class="meta-item" style="grid-column: 1 / -1;">
              <i class="fa-solid fa-clock meta-icon"></i> ${job.shift_timings}
            </div>
          </div>

          <div class="tags-container">
            ${eventBadge}
            ${mealServicesHtml}
            ${tagsHtml}
          </div>
        </div>

        <div class="job-card-footer">
          <div class="job-card-primary-actions">
            <button class="btn-apply-now" onclick="openApplyModal('${job.id}')">
              <i class="fa-solid fa-paper-plane"></i> Apply Now
            </button>
            <button class="btn-call-direct" onclick="directCallEmployer('${job.contact_phone}', '${job.id}')">
              <i class="fa-solid fa-phone"></i> Call
            </button>
          </div>
          <button class="btn-directions" onclick="openDirections('${job.location}')">
            <i class="fa-solid fa-location-arrow"></i> Directions
          </button>
        </div>
      </div>
    `;
  }).join("");
}

function openDirections(location) {
  const mapQuery = encodeURIComponent(location || "job location");
  window.open(`https://www.google.com/maps/search/?api=1&query=${mapQuery}`, '_blank');
}

function renderRecentActivity(jobs) {
  const ribbon = document.getElementById("recent-activity-ribbon");
  if (!ribbon) return;

  const sample = jobs.slice(0, 6);
  ribbon.innerHTML = sample.map(job => `
    <div class="mini-activity-card" onclick="openApplyModal('${job.id}')">
      <div class="mini-title">${job.title}</div>
      <div style="font-size: 0.75rem; color: var(--text-muted); margin: 2px 0;">${job.location}</div>
      <div class="mini-rate">${job.rate_formatted}</div>
    </div>
  `).join("");
}

// ==========================================
// SEARCH & FILTER HANDLERS
// ==========================================

function filterByCategory(catId) {
  state.activeCategory = catId;
  document.getElementById("global-category-select").value = catId;
  loadCategories();
  loadJobs();
}

function setQuickFilter(filter) {
  state.activeQuickFilter = filter;
  state.activeFilterTag = "all";
  if (filter === "all") {
    state.activeMealService = "all";
    updateMealServiceSelection();
    document.getElementById("meal-filter-menu").open = false;
  }
  document.querySelectorAll("#job-filters > button.filter-pill").forEach(button => {
    button.classList.toggle("active", button.id === `quick-filter-${filter.replace("_", "-")}`);
  });
  loadJobs();
}

function setMealServiceFilter(mealService) {
  state.activeMealService = mealService;
  updateMealServiceSelection();
  loadJobs();
}

function updateMealServiceSelection() {
  document.querySelectorAll(".meal-service-option").forEach(option => {
    const isSelected = option.dataset.mealService === state.activeMealService;
    option.classList.toggle("active", isSelected);
    option.setAttribute("aria-pressed", String(isSelected));
  });
}

function filterByTag(tag) {
  state.activeFilterTag = tag;
  if (tag !== "all") state.activeQuickFilter = "all";
  document.querySelectorAll("#job-filters > button.filter-pill").forEach(button => {
    button.classList.toggle("active", button.id === "quick-filter-all" && state.activeQuickFilter === "all");
  });
  loadJobs();
}

function triggerSearch() {
  const input = document.getElementById("global-search-input").value;
  const category = document.getElementById("global-category-select").value;

  state.activeKeyword = input;
  state.activeCategory = category;
  loadJobs();
}

function handleSearchKeyup(e) {
  if (e.key === "Enter") {
    triggerSearch();
  }
}

function resetSearch() {
  state.activeKeyword = "";
  state.activeCategory = "all";
  state.activeFilterTag = "all";
  state.activeQuickFilter = "all";
  state.activeMealService = "all";
  document.getElementById("global-search-input").value = "";
  document.getElementById("global-category-select").value = "all";
  updateMealServiceSelection();
  document.getElementById("meal-filter-menu").open = false;
  setQuickFilter("all");
  loadCategories();
}

// ==========================================
// MODAL & AUTHENTICATION LOGIC (MOBILE FIRST)
// ==========================================

function openAuthModal() {
  showModal("auth-modal");
  document.getElementById("auth-step-1").style.display = "block";
  document.getElementById("auth-step-2").style.display = "none";
  document.getElementById("auth-step-3").style.display = "none";
}

function openAuthOrProfileModal() {
  if (state.user.isAuthenticated) {
    showToast(`Logged in as +91 ${state.user.mobile} (${state.user.role.toUpperCase()})`);
  } else {
    openAuthModal();
  }
}

async function submitMobileAuth() {
  const mobile = document.getElementById("auth-mobile-input").value.trim();
  if (mobile.length < 10) {
    showToast("Please enter a valid 10-digit mobile number.", "warning");
    return;
  }

  try {
    const res = await fetch("/api/auth/send-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mobile })
    });
    const data = await res.json();
    if (res.ok) {
      state.user.mobile = mobile;
      document.getElementById("otp-mobile-display").innerText = `+91 ${mobile}`;
      document.getElementById("auth-step-1").style.display = "none";
      document.getElementById("auth-step-2").style.display = "block";
      showToast(`OTP Code sent! Demo code: 123456`);
    } else {
      showToast(data.detail || "Error sending OTP", "error");
    }
  } catch (err) {
    console.error(err);
  }
}

function moveOtpFocus(current, nextId) {
  if (current.value.length >= 1 && nextId) {
    document.getElementById(nextId).focus();
  }
}

async function submitOtpVerify() {
  let otp = "";
  document.querySelectorAll(".otp-digit").forEach(d => otp += d.value);
  if (otp.length < 6) otp = "123456"; // Demo fallback

  try {
    const res = await fetch("/api/auth/verify-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mobile: state.user.mobile, otp })
    });
    const data = await res.json();
    if (res.ok) {
      state.user.isAuthenticated = true;
      document.getElementById("auth-step-2").style.display = "none";
      document.getElementById("auth-step-3").style.display = "block";
      showToast("OTP Verified successfully!");
    } else {
      showToast(data.detail || "Verification failed", "error");
    }
  } catch (err) {
    console.error(err);
  }
}

function selectRole(role) {
  state.user.role = role;
  document.getElementById("role-seeker").classList.remove("selected");
  document.getElementById("role-employer").classList.remove("selected");
  document.getElementById(`role-${role}`).classList.add("selected");
}

async function finishOnboarding() {
  const loc = document.getElementById("onboard-location").value;
  state.user.location = loc;

  try {
    await fetch("/api/auth/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.user)
    });

    localStorage.setItem("findzo_user", JSON.stringify(state.user));
    updateUserNavDisplay();
    closeModal("auth-modal");
    showToast("Profile set up complete! Welcome to Findzo.");
  } catch (err) {
    console.error(err);
  }
}

function updateUserNavDisplay() {
  const initialElem = document.getElementById("user-avatar-initial");
  const nameElem = document.getElementById("user-profile-name-nav");

  if (state.user.isAuthenticated) {
    initialElem.innerText = state.user.mobile.charAt(0);
    nameElem.innerText = `+91 ${state.user.mobile.slice(-4)}`;
  } else {
    initialElem.innerText = "F";
    nameElem.innerText = "Sign In";
  }
}

function resendOtp() {
  showToast("Demo OTP Code resent: 123456");
}

// ==========================================
// LOCATION SELECTOR MODAL & GEOLOCATION
// ==========================================

function openLocationModal() {
  showModal("location-modal");
}

function setPopularLocation(city, pin) {
  document.getElementById("manual-pincode-input").value = `${city} (${pin})`;
}

function detectGeolocation() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = `${pos.coords.latitude.toFixed(2)}, ${pos.coords.longitude.toFixed(2)}`;
        document.getElementById("manual-pincode-input").value = `GPS: ${coords} (Andheri East)`;
        showToast("Location detected via GPS!");
      },
      (err) => {
        showToast("GPS Permission denied. Using default location.", "warning");
      }
    );
  } else {
    showToast("Geolocation not supported by browser.", "warning");
  }
}

function saveLocationPreference() {
  const val = document.getElementById("manual-pincode-input").value;
  if (val) {
    state.user.location = val;
    state.user.pincode = val.match(/\b\d{6}\b/)?.[0] || "";
    document.getElementById("current-location-text").innerText = val;
    closeModal("location-modal");
    showToast(`Location set to: ${val}`);
    loadJobs();
  }
}

// ==========================================
// QUICK APPLY & CONTACT UNLOCK MODAL
// ==========================================

function openApplyModal(jobId) {
  const job = state.allJobs.find(j => j.id === jobId);
  if (!job) return;

  state.selectedJobForApply = job;
  document.getElementById("apply-modal-title").innerText = `Apply: ${job.title}`;
  document.getElementById("apply-modal-rate").innerText = job.rate_formatted;
  document.getElementById("apply-modal-employer").innerText = job.employer_name;
  document.getElementById("apply-modal-desc").innerText = `Requirement in ${job.location}. Shift: ${job.shift_timings}.`;

  showModal("apply-modal");
}

async function confirmJobApplication() {
  if (!state.selectedJobForApply) return;

  const phone = document.getElementById("apply-applicant-phone").value;
  const notes = document.getElementById("apply-applicant-notes").value;

  try {
    const res = await fetch(`/api/jobs/${state.selectedJobForApply.id}/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: state.selectedJobForApply.id,
        applicant_mobile: phone,
        applicant_name: "Local Job Seeker",
        notes: notes
      })
    });
    const data = await res.json();
    closeModal("apply-modal");

    showToast(`Applied! Direct Call Unlocked: ${data.application.contact_phone}`);
    loadJobs();
  } catch (err) {
    console.error(err);
  }
}

function directCallEmployer(phone, jobId) {
  const job = state.allJobs.find(j => j.id === jobId);
  const title = job ? job.title : "Job Requirement";
  showToast(`Dialing Employer for "${title}": ${phone}`);
  window.location.href = `tel:${phone.replace(/\s+/g, '')}`;
}

// ==========================================
// SAVED JOBS & EMPLOYER POST JOB MODAL
// ==========================================

async function toggleSaveJob(jobId) {
  try {
    const res = await fetch(`/api/jobs/${jobId}/save?mobile=${state.user.mobile}`, {
      method: "POST"
    });
    const data = await res.json();

    if (data.is_saved) {
      if (!state.savedJobIds.includes(jobId)) state.savedJobIds.push(jobId);
    } else {
      state.savedJobIds = state.savedJobIds.filter(id => id !== jobId);
    }

    localStorage.setItem("findzo_saved_jobs", JSON.stringify(state.savedJobIds));
    updateSavedCountBadge();
    showToast(data.message);
    loadJobs();
  } catch (err) {
    console.error(err);
  }
}

function updateSavedCountBadge() {
  const badge = document.getElementById("saved-jobs-count");
  if (badge) badge.innerText = state.savedJobIds.length;
}

function openSavedJobsModal() {
  if (state.savedJobIds.length === 0) {
    showToast("No saved jobs yet! Click the bookmark icon on any job card.", "warning");
  } else {
    showToast(`Showing ${state.savedJobIds.length} saved job bookmarks!`);
  }
}

function openApplicationsModal() {
  showToast("Your Active Job Applications: 2 Pending Response.");
}

function openPostJobModal() {
  showModal("post-job-modal");
}

async function submitNewJobPost(withPayment = false) {
  const title = document.getElementById("post-title").value;
  const category = document.getElementById("post-category").value;
  const mealService = document.getElementById("post-meal-service").value;
  const eventDate = document.getElementById("post-event-date").value || null;
  const rate = parseFloat(document.getElementById("post-rate").value) || 800;
  const rateType = document.getElementById("post-rate-type").value;
  const location = document.getElementById("post-location").value || "Andheri, Mumbai";
  const timings = document.getElementById("post-timings").value || "8:00 AM - 5:30 PM";
  const employer = document.getElementById("post-employer").value || "Local Employer";
  const phone = document.getElementById("post-phone").value || "+91 98200 99887";
  const description = document.getElementById("post-description").value || "Need skilled worker for immediate daily shift.";
  const pincode = location.match(/\b\d{6}\b/)?.[0] || "";

  if (!title) {
    showToast("Please enter a job title.", "warning");
    return;
  }
  if (!eventDate) {
    showToast("Please select the event date.", "warning");
    return;
  }

  const jobPayload = {
    title, category, rate, rate_type: rateType,
    location, pincode, shift_timings: timings,
    meal_services: [mealService], event_date: eventDate,
    employer_name: employer, contact_phone: phone, description,
    tags: withPayment ? ["Featured Paid Posting", "Verified Employer", "Paid Daily"] : ["Paid Daily", "Same-Day Start"]
  };

  if (withPayment) {
    showToast("Initiating ₹199 Razorpay Payment Checkout...");
    try {
      const orderRes = await fetch("/api/payments/create-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount: 199.0,
          purpose: `Featured Job Post: ${title}`,
          user_mobile: phone
        })
      });
      const orderData = await orderRes.json();

      if (window.Razorpay && orderData.mode === "live_razorpay") {
        const options = {
          "key": orderData.key_id,
          "amount": orderData.amount_paise,
          "currency": "INR",
          "name": "Findzo Local Staffing",
          "description": `Featured Job: ${title}`,
          "order_id": orderData.order_id,
          "handler": async function(response) {
            await fetch("/api/payments/verify", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                order_id: response.razorpay_order_id,
                payment_id: response.razorpay_payment_id,
                signature: response.razorpay_signature,
                user_mobile: phone,
                purpose: "Featured Job Posting"
              })
            });
            await finalizeJobPost(jobPayload);
          }
        };
        const rzp = new window.Razorpay(options);
        rzp.open();
        return;
      } else {
        // Simulated / Demo Payment Verification
        await fetch("/api/payments/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            order_id: orderData.order_id,
            payment_id: `pay_demo_${Date.now()}`,
            signature: "demo_sig_ok",
            user_mobile: phone,
            purpose: "Featured Job Posting"
          })
        });
        showToast("Demo Payment Verified (₹199)! Publishing featured job...");
        await finalizeJobPost(jobPayload);
        return;
      }
    } catch (err) {
      console.error(err);
      showToast("Payment initialization failed, publishing standard job...", "warning");
    }
  }

  await finalizeJobPost(jobPayload);
}

async function finalizeJobPost(jobPayload) {
  try {
    const res = await fetch("/api/jobs/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(jobPayload)
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Could not publish the job. Please try again.");
    }
    closeModal("post-job-modal");
    showToast(data.message || "Job published successfully!");
    await loadJobs();
  } catch (err) {
    console.error(err);
    showToast(err.message || "Could not publish the job. Please try again.", "warning");
  }
}

// ==========================================
// UTILITY FUNCTIONS & MULTI-LANGUAGE
// ==========================================

function showModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.style.display = "flex";
  setTimeout(() => {
    modal.classList.add("active");
  }, 10);
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove("active");
  setTimeout(() => {
    modal.style.display = "none";
  }, 250);
}

function focusMobileSearch() {
  document.getElementById("global-search-input").focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showToast(message, type = "info") {
  const toast = document.getElementById("toast-bar");
  const msgElem = document.getElementById("toast-message");
  if (!toast || !msgElem) return;

  msgElem.innerText = message;
  toast.classList.add("show");

  setTimeout(() => {
    toast.classList.remove("show");
  }, 3500);
}
