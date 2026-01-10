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

    // Function to check access
    const checkAccess = function () {
        console.log("LMS Tracker: Checking access...");
        const path = window.location.pathname;
        const matches = path.match(/\/courses\/([^/]+)\/learn\/([^/]+)/);

        if (matches) {
            const course = decodeURIComponent(matches[1]);
            const lesson_number = matches[2]; // e.g., 1-2

            // Check if user is Guest
            const isGuest = frappe.session.user === "Guest";

            // Avoid redundant checks for same lesson unless it was blocked and we want to re-check
            if (window.currentCheckedLesson === lesson_number && !$('.lms-access-denied-overlay').length) return;
            window.currentCheckedLesson = lesson_number;

            console.log(`LMS Tracker: Verifying access for ${course} lesson ${lesson_number} (User: ${frappe.session.user})`);

            frappe.call({
                method: 'lms_reports.lms_reports.api.check_lesson_access',
                args: {
                    course: course,
                    lesson_number: lesson_number
                },
                callback: function (r) {
                    console.log("LMS Tracker: Access check response:", r.message);
                    if (r.message && !r.message.can_access) {
                        showAccessDenied(r.message.reason, isGuest);
                    } else {
                        // Access granted, hide any previous warning
                        $('.lms-access-denied-overlay').remove();
                    }
                },
                error: function (err) {
                    console.error("LMS Tracker: Access check failed", err);
                }
            });
        }
    };

    const showAccessDenied = function (reason, isGuest) {
        // Remove any existing overlay
        $('.lms-access-denied-overlay').remove();

        const buttonText = isGuest ? "Kirish (Sign In)" : "Orqaga qaytish";
        const buttonAction = isGuest ? "window.location.href='/login'" : "window.history.back()";
        const title = isGuest ? "Kursga kirish" : "Dars bloklangan";
        const emoji = isGuest ? "🔑" : "🔒";

        // Create overlay
        const overlay = $(`
            <div class="lms-access-denied-overlay" style="
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
                font-family: inherit;
            ">
                <div style="max-width: 500px; background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                    <div style="font-size: 64px; margin-bottom: 20px;">${emoji}</div>
                    <h2 style="color: #1a1a1a; margin-bottom: 15px; font-weight: 700;">${title}</h2>
                    <p style="font-size: 18px; line-height: 1.6; color: #666; margin-bottom: 30px;">${reason}</p>
                    <button class="btn btn-primary btn-lg" style="padding: 12px 30px; font-weight: 600; border-radius: 10px;" onclick="${buttonAction}">${buttonText}</button>
                    <div style="margin-top: 25px;">
                        <a href="/lms/courses" style="color: #888; text-decoration: none; font-size: 14px;">← Kurslar ro'yxatiga qaytish</a>
                    </div>
                </div>
            </div>
        `);

        $('body').append(overlay);
        // Disable scroll
        $('body').css('overflow', 'hidden');
    };

    // Attempt to attach
    attachTracker();
    checkAccess();

    // Watch for dynamic content changes (SPA navigation)
    // We observe a container that is likely to change on navigation
    const observer = new MutationObserver((mutations) => {
        // Check if the URL changed
        if (window.lastPathname !== window.location.pathname) {
            window.lastPathname = window.location.pathname;
            console.log("LMS Tracker: Path changed to", window.lastPathname);
            checkAccess();
        }
        attachTracker();
    });

    window.lastPathname = window.location.pathname;
    observer.observe(document.body, { childList: true, subtree: true });

    // Also handle popstate (back/forward)
    window.addEventListener('popstate', () => {
        console.log("LMS Tracker: Popstate triggered");
        checkAccess();
    });
});
