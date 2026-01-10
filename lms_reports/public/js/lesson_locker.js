/**
 * Lesson Locker - Frontend
 * Prevents access to locked lessons
 */

(function() {
	'use strict';

	console.log("=== Lesson Locker Active ===");

	// Check lesson access before navigation
	function checkLessonAccess(lessonName, courseName) {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: 'lms_reports.lesson_locker.check_lesson_access',
				args: {
					lesson: lessonName,
					course: courseName
				},
				callback: function(r) {
					if (r.message) {
						resolve(r.message);
					} else {
						reject('No response');
					}
				},
				error: function(err) {
					console.error("Error checking lesson access:", err);
					reject(err);
				}
			});
		});
	}

	// Block lesson link if locked
	async function lockLessonsInOutline() {
		console.log("Scanning for lessons to lock...");

		// Find all lesson links in course outline
		const lessonLinks = document.querySelectorAll('a[href*="/learn/"]');

		lessonLinks.forEach(async (link) => {
			const href = link.getAttribute('href');
			const match = href.match(/\/learn\/([^\/]+)\/([^\/]+)/);

			if (match) {
				const courseName = match[1];
				const lessonName = match[2];

				try {
					const access = await checkLessonAccess(lessonName, courseName);

					if (!access.can_access) {
						// Lock this lesson
						link.classList.add('lesson-locked');
						link.style.opacity = '0.5';
						link.style.cursor = 'not-allowed';
						link.style.pointerEvents = 'none';

						// Add lock icon
						if (!link.querySelector('.lock-icon')) {
							const lockIcon = document.createElement('span');
							lockIcon.className = 'lock-icon';
							lockIcon.innerHTML = ' 🔒';
							lockIcon.title = access.reason;
							link.appendChild(lockIcon);
						}

						// Prevent click
						link.addEventListener('click', function(e) {
							e.preventDefault();
							e.stopPropagation();

							frappe.msgprint({
								title: __('Lesson Locked'),
								message: access.reason + '<br><br>' +
									(access.previous_lesson_title ?
										`Please complete: <strong>${access.previous_lesson_title}</strong>` : ''),
								indicator: 'orange'
							});

							return false;
						}, true);
					} else {
						// Lesson is accessible - show checkmark if completed
						const status = await getLessonStatus(lessonName);
						if (status && status.is_completed) {
							if (!link.querySelector('.complete-icon')) {
								const checkIcon = document.createElement('span');
								checkIcon.className = 'complete-icon';
								checkIcon.innerHTML = ' ✅';
								checkIcon.title = 'Completed';
								link.appendChild(checkIcon);
							}
						}
					}
				} catch (err) {
					console.error(`Error locking lesson ${lessonName}:`, err);
				}
			}
		});
	}

	// Get lesson completion status
	function getLessonStatus(lessonName) {
		return new Promise((resolve) => {
			frappe.call({
				method: 'lms_reports.lesson_locker.get_lesson_completion_status',
				args: {
					lesson: lessonName,
					member: frappe.session.user
				},
				callback: function(r) {
					resolve(r.message);
				}
			});
		});
	}

	// Block direct navigation to locked lessons
	function interceptLessonNavigation() {
		// Get current URL
		const path = window.location.pathname;
		const match = path.match(/\/learn\/([^\/]+)\/([^\/]+)/);

		if (match) {
			const courseName = match[1];
			const lessonName = match[2];

			checkLessonAccess(lessonName, courseName).then(access => {
				if (!access.can_access) {
					// Show error and redirect to course
					frappe.msgprint({
						title: __('Lesson Locked'),
						message: access.reason + '<br><br>' +
							(access.previous_lesson_title ?
								`Please complete: <strong>${access.previous_lesson_title}</strong>` : ''),
						indicator: 'red'
					});

					// Redirect to course page
					setTimeout(() => {
						window.location.href = `/courses/${courseName}`;
					}, 2000);
				}
			}).catch(err => {
				console.error("Error checking current lesson:", err);
			});
		}
	}

	// Run on page load
	function init() {
		// Lock lessons in sidebar/outline
		setTimeout(lockLessonsInOutline, 1000);

		// Check current page
		interceptLessonNavigation();

		// Re-run on navigation (for SPA)
		window.addEventListener('hashchange', () => {
			setTimeout(lockLessonsInOutline, 500);
			interceptLessonNavigation();
		});

		// Watch for DOM changes
		const observer = new MutationObserver(() => {
			setTimeout(lockLessonsInOutline, 500);
		});

		observer.observe(document.body, {
			childList: true,
			subtree: true
		});
	}

	// Start when DOM is ready
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}

	// Also handle Frappe's page-change event
	$(document).on('page-change', init);

})();
