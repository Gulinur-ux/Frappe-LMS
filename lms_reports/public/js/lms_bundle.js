/**
 * LMS Video & Progress Tracker v3.0
 * Tracks video playback, quiz attempts, and lesson completion
 * URL Pattern: /lms/courses/{course}/learn/{lesson_number}
 */

(function () {
    'use strict';

    console.log("=== LMS Tracker v3.0 Starting ===");

    // Debounce utility to prevent excessive API calls
    const debounce = (func, wait) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    };

    // Get lesson info from URL
    function getLessonInfo() {
        const path = window.location.pathname;
        console.log("LMS Tracker: Current path:", path);

        // Match: /lms/courses/course-name/learn/1-1 or /courses/course-name/learn/1.1
        const matches = path.match(/\/(?:lms\/)?courses\/([^\/]+)\/learn\/([0-9]+[\-\.][0-9]+)/);

        if (matches) {
            const course = decodeURIComponent(matches[1]);
            const lessonNumber = matches[2];
            console.log(`LMS Tracker: Found course=${course}, lesson_number=${lessonNumber}`);
            return { course, lessonNumber };
        }

        // Fallback: /lms/courses/course-name/lesson/lesson-name
        const fallbackMatches = path.match(/\/(?:lms\/)?courses\/([^\/]+)\/lesson\/([^\/]+)/);
        if (fallbackMatches) {
            const course = decodeURIComponent(fallbackMatches[1]);
            const lesson = decodeURIComponent(fallbackMatches[2]);
            console.log(`LMS Tracker: Found course=${course}, lesson=${lesson} (fallback)`);
            return { course, lesson };
        }

        console.log("LMS Tracker: No lesson context found in URL");
        return null;
    }

    // Get lesson name from lesson number via API
    async function getLessonFromNumber(course, lessonNumber) {
        return new Promise((resolve, reject) => {
            frappe.call({
                method: 'lms_reports.lms_reports.api.get_lesson_from_number',
                args: { course, lesson_number: lessonNumber },
                async: true,
                callback: function (r) {
                    if (r.message && r.message.lesson) {
                        resolve(r.message.lesson);
                    } else {
                        reject(new Error("Lesson not found"));
                    }
                },
                error: function (err) {
                    console.error("LMS Tracker: Failed to get lesson from number", err);
                    reject(err);
                }
            });
        });
    }

    // Track video progress
    function trackProgress(videoEl, lessonInfo) {
        if (!lessonInfo) return;
        if (frappe.session.user === "Guest") return;

        const speed = videoEl.playbackRate + 'x';
        const currentTime = videoEl.currentTime;
        const duration = videoEl.duration;

        if (!duration || isNaN(duration)) {
            console.log("LMS Tracker: Video duration not available yet");
            return;
        }

        console.log(`LMS Tracker: Tracking - Speed: ${speed}, Time: ${currentTime}/${duration}`);

        frappe.call({
            method: 'lms_reports.lms_reports.api.track_lesson_watch',
            args: {
                lesson_number: lessonInfo.lessonNumber,
                lesson: lessonInfo.lesson || null,
                course: lessonInfo.course,
                video_speed: speed,
                watched_duration: currentTime,
                video_total_duration: duration,
                start_time: 0,
                end_time: currentTime
            },
            callback: function (r) {
                if (r.message && r.message.success) {
                    console.log(`LMS Tracker: Progress saved - ${r.message.completion_percentage}%`);
                }
            },
            error: function (err) {
                console.error("LMS Tracker: Failed to save progress", err);
            }
        });
    }

    // Create debounced version (2 second delay)
    const trackProgressDebounced = debounce(trackProgress, 2000);

    // Attach tracker to video elements
    function attachVideoTrackers() {
        const lessonInfo = getLessonInfo();
        if (!lessonInfo) return;

        const players = document.querySelectorAll('video, audio, iframe[src*="youtube"], iframe[src*="vimeo"]');
        console.log(`LMS Tracker: Found ${players.length} media elements`);

        players.forEach(player => {
            if (player.dataset.lmsTrackerAttached) return;

            // For HTML5 video/audio
            if (player.tagName === 'VIDEO' || player.tagName === 'AUDIO') {
                // Track on speed change
                player.addEventListener('ratechange', () => {
                    console.log("LMS Tracker: Speed changed to", player.playbackRate);
                    trackProgressDebounced(player, lessonInfo);
                });

                // Track on pause
                player.addEventListener('pause', () => {
                    console.log("LMS Tracker: Video paused");
                    trackProgress(player, lessonInfo); // Immediate on pause
                });

                // Track on video end
                player.addEventListener('ended', () => {
                    console.log("LMS Tracker: Video ended");
                    trackProgress(player, lessonInfo);
                });

                // Track periodically while playing (every 30 seconds)
                let lastTrackTime = 0;
                player.addEventListener('timeupdate', () => {
                    const now = Date.now();
                    if (now - lastTrackTime > 30000) {
                        trackProgressDebounced(player, lessonInfo);
                        lastTrackTime = now;
                    }
                });

                player.dataset.lmsTrackerAttached = 'true';
                console.log("LMS Tracker: Attached to video/audio element");
            }
        });
    }

    // Check lesson access (sequential access control)
    function checkLessonAccess() {
        const lessonInfo = getLessonInfo();
        if (!lessonInfo) return;

        if (frappe.session.user === "Guest") {
            showAccessDenied("Ushbu darsni ko'rish uchun tizimga kiring.", true);
            return;
        }

        console.log("LMS Tracker: Checking access for", lessonInfo);

        frappe.call({
            method: 'lms_reports.lms_reports.api.check_lesson_access',
            args: {
                course: lessonInfo.course,
                lesson_number: lessonInfo.lessonNumber,
                lesson: lessonInfo.lesson
            },
            callback: function (r) {
                console.log("LMS Tracker: Access check result:", r.message);
                if (r.message && !r.message.can_access) {
                    showAccessDenied(r.message.reason, false);
                } else {
                    // Access granted - remove any overlay
                    removeAccessOverlay();
                }
            },
            error: function (err) {
                console.error("LMS Tracker: Access check failed", err);
            }
        });
    }

    function showAccessDenied(reason, isGuest) {
        removeAccessOverlay();

        const buttonText = isGuest ? "Kirish (Sign In)" : "Orqaga qaytish";
        const buttonAction = isGuest ? "window.location.href='/login'" : "window.history.back()";
        const title = isGuest ? "Kursga kirish" : "Dars bloklangan";
        const emoji = isGuest ? "🔑" : "🔒";

        const overlay = document.createElement('div');
        overlay.className = 'lms-access-denied-overlay';
        overlay.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.98);
                z-index: 99999;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 20px;
                text-align: center;
            ">
                <div style="max-width: 500px; background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                    <div style="font-size: 64px; margin-bottom: 20px;">${emoji}</div>
                    <h2 style="color: #1a1a1a; margin-bottom: 15px; font-weight: 700;">${title}</h2>
                    <p style="font-size: 18px; line-height: 1.6; color: #666; margin-bottom: 30px;">${reason}</p>
                    <button onclick="${buttonAction}" class="btn btn-primary btn-lg" style="padding: 12px 30px; font-weight: 600; border-radius: 10px;">${buttonText}</button>
                    <div style="margin-top: 25px;">
                        <a href="/lms/courses" style="color: #888; text-decoration: none; font-size: 14px;">← Kurslar ro'yxatiga qaytish</a>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';
    }

    function removeAccessOverlay() {
        const existing = document.querySelector('.lms-access-denied-overlay');
        if (existing) {
            existing.remove();
            document.body.style.overflow = '';
        }
    }

    // Initialize
    function init() {
        console.log("LMS Tracker: Initializing...");

        // Wait for frappe to be ready
        if (typeof frappe === 'undefined' || !frappe.session) {
            console.log("LMS Tracker: Waiting for frappe...");
            setTimeout(init, 500);
            return;
        }

        // Check access first
        checkLessonAccess();

        // Attach video trackers
        setTimeout(attachVideoTrackers, 1000);

        // Watch for dynamic content changes (SPA)
        const observer = new MutationObserver((mutations) => {
            attachVideoTrackers();
        });

        observer.observe(document.body, { childList: true, subtree: true });

        // Handle URL changes
        let lastPath = window.location.pathname;
        const urlObserver = new MutationObserver(() => {
            if (window.location.pathname !== lastPath) {
                lastPath = window.location.pathname;
                console.log("LMS Tracker: URL changed to", lastPath);
                checkLessonAccess();
                setTimeout(attachVideoTrackers, 500);
            }
        });
        urlObserver.observe(document, { childList: true, subtree: true });

        // Handle back/forward navigation
        window.addEventListener('popstate', () => {
            console.log("LMS Tracker: Popstate event");
            checkLessonAccess();
            setTimeout(attachVideoTrackers, 500);
        });
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();

console.log("LMS Tracker v3.0 loaded");
