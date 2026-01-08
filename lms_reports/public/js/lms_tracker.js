frappe.ready(function () {
    if (!cur_frm || cur_frm.doctype !== "Course Lesson") {
        // We might be in the web view, checking for lesson container
        if (!$('.lesson-content').length && !$('.course-lesson').length) return;
    }

    // Function to track progress
    const trackProgress = function (videoEl) {
        let lesson = null;
        let course = null;

        // Try to get context from URL or page
        const path = window.location.pathname;
        const matches = path.match(/\/courses\/([^/]+)\/lesson\/([^/]+)/);

        if (matches) {
            course = decodeURIComponent(matches[1]);
            lesson = decodeURIComponent(matches[2]);
        } else {
            // Fallback for desk or other views
            return;
        }

        const speed = videoEl.playbackRate + 'x';
        const currentTime = videoEl.currentTime;
        const duration = videoEl.duration;

        frappe.call({
            method: 'lms_reports.lms_reports.api.track_lesson_watch',
            args: {
                lesson: lesson,
                course: course,
                video_speed: speed,
                watched_duration: currentTime, // Reporting current position/watched amount
                video_total_duration: duration,
                start_time: 0, // Simplified for now
                end_time: currentTime
            },
            callback: function (r) {
                // success
            },
            error: function (r) {
                // silent fail
            }
        });
    };

    // Attach to Plyr if it exists
    const attachTracker = function () {
        const players = Array.from(document.querySelectorAll('video, audio'));

        players.forEach(player => {
            if (player.dataset.trackerAttached) return;

            // Track speed change
            player.addEventListener('ratechange', (e) => {
                trackProgress(e.target);
            });

            // Track pause (often end of a viewing session)
            player.addEventListener('pause', (e) => {
                trackProgress(e.target);
            });

            // Track end
            player.addEventListener('ended', (e) => {
                trackProgress(e.target);
            });

            // Track periodically (every 30 seconds)
            let lastTrack = 0;
            player.addEventListener('timeupdate', (e) => {
                const now = Date.now();
                if (now - lastTrack > 30000) {
                    trackProgress(e.target);
                    lastTrack = now;
                }
            });

            player.dataset.trackerAttached = true;
            console.log("LMS Tracker attached to video");
        });
    };

    // Attempt to attach
    attachTracker();

    // Watch for dynamic content changes (SPA navigation)
    const observer = new MutationObserver((mutations) => {
        attachTracker();
    });

    observer.observe(document.body, { childList: true, subtree: true });
});
