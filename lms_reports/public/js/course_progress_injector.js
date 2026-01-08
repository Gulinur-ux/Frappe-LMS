/**
 * Enhanced Course Progress Injector for LMS Reports
 * Uses bulk API for efficiency and matches Frappe School UI
 */

(function () {
	'use strict';

	console.log("=== LMS Progress Injector v2.1 Starting ===");

	// Don't return early for Guest yet, let's see if we even find cards
	// if (frappe.session.user === "Guest") {
	//    console.log("User is Guest, skipping progress fetch");
	//    return;
	// }

	let isProcessing = false;

	function injectProgress() {
		if (isProcessing) return;

		console.log("Scanning for cards...");
		const cards = document.querySelectorAll('.course-card, [class*="CourseCard"], .card, .common-card-style');
		console.log(`Found ${cards.length} potential cards`);

		const cardsToProcess = [];
		const courseNames = [];

		cards.forEach((card, index) => {
			if (card.dataset.progressInjected) return;

			// Try multiple link selectors
			const link = card.querySelector('a[href*="/courses/"], a[href*="/course/"]');
			if (link) {
				const href = link.getAttribute('href');
				console.log(`Card ${index} href: ${href}`);

				// Flexible regex to match both /courses/name and /lms/courses/name
				const match = href.match(/\/(?:lms\/)?courses?\/([^\/\?#]+)/);

				if (match) {
					const courseName = match[1];
					console.log(`Matched course: ${courseName}`);
					card.dataset.courseName = courseName;
					cardsToProcess.push(card);
					if (!courseNames.includes(courseName)) {
						courseNames.push(courseName);
					}
				} else {
					console.log(`Href ${href} did not match course regex`);
				}
			} else {
				// If no link found, maybe it's the data-course-name attribute?
				const courseName = card.dataset.course || card.getAttribute('data-course');
				if (courseName) {
					console.log(`Found course from data attribute: ${courseName}`);
					card.dataset.courseName = courseName;
					cardsToProcess.push(card);
					if (!courseNames.includes(courseName)) {
						courseNames.push(courseName);
					}
				}
			}
		});

		if (cardsToProcess.length === 0) {
			console.log("No new cards to process");
			return;
		}

		if (frappe.session.user === "Guest") {
			console.log("User is Guest, marking cards as processed without fetching progress");
			cardsToProcess.forEach(card => card.dataset.progressInjected = "true");
			return;
		}

		isProcessing = true;
		console.log(`Fetching progress for courses: ${courseNames.join(', ')}`);

		frappe.call({
			method: 'lms_reports.progress_tracker.get_bulk_course_progress',
			args: { courses: courseNames },
			callback: function (r) {
				console.log("Progress received:", r.message);
				if (r.message) {
					cardsToProcess.forEach(card => {
						const courseName = card.dataset.courseName;
						const progressData = r.message[courseName];

						if (progressData) {
							const progress = Math.round(progressData.overall_progress || 0);
							console.log(`Rendering ${progress}% for ${courseName}`);
							renderProgress(card, progress);
						}
						card.dataset.progressInjected = "true";
					});
				}
				isProcessing = false;
			},
			error: function (err) {
				console.error("Progress fetch error:", err);
				isProcessing = false;
			}
		});
	}

	function renderProgress(card, progress) {
		// Find existing content container or footer to insert before
		const content = card.querySelector('.course-card-content, .card-body, .card-content') || card;

		// Find footer or instructors section to insert before
		const footer = content.querySelector('.course-card-footer, .card-footer, .course-card-instructors');

		const progressHTML = `
            <div class="lms-custom-progress-container">
                <div class="lms-card-progress-bar-wrapper">
                    <div class="lms-card-progress-bar-fill" style="width: ${progress}%"></div>
                </div>
                <div class="lms-progress-text">${progress}% completed (LR)</div>
            </div>
        `;

		const tempDiv = document.createElement('div');
		tempDiv.innerHTML = progressHTML.trim();
		const progressEl = tempDiv.firstChild;

		if (footer) {
			footer.parentNode.insertBefore(progressEl, footer);
		} else {
			content.appendChild(progressEl);
		}
	}

	// Debounced listener
	let timeout;
	const observer = new MutationObserver(() => {
		clearTimeout(timeout);
		timeout = setTimeout(injectProgress, 500);
	});

	// Start
	console.log("Injector waiting for load...");
	if (document.readyState === 'complete') {
		setTimeout(injectProgress, 1500);
	} else {
		window.addEventListener('load', () => setTimeout(injectProgress, 1500));
	}

	observer.observe(document.body, { childList: true, subtree: true });

	// Handle hash changes for SPA (LMS uses Vue)
	window.addEventListener('hashchange', () => setTimeout(injectProgress, 500));

	// Also run on page transitions if Frappe's router is used
	$(document).on('page-change', () => setTimeout(injectProgress, 500));

})();
