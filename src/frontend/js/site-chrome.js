/**
 * Shared site header/footer for PlayNexus static pages.
 * Set body[data-root-prefix] to ".." for one level under frontend root (games, community, about).
 * Set body[data-chrome-active] to hub | games | apps | community | about for nav highlight.
 * Optional body[data-chrome-pill] for a small label next to the logo.
 */
(function () {
    "use strict";

    function esc(s) {
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/"/g, "&quot;");
    }

    function joinPrefix(prefix, path) {
        var p = prefix || "";
        if (!p) return path;
        return p.replace(/\/?$/, "") + "/" + path.replace(/^\//, "");
    }

    function headerHTML(prefix, active, pill) {
        var hub = joinPrefix(prefix, "index.html");
        var games = joinPrefix(prefix, "games/games.html");
        var community = joinPrefix(prefix, "community/community.html");
        var about = joinPrefix(prefix, "about/about.html");
        var appsHash = joinPrefix(prefix, "index.html") + "#apps";

        function cls(name) {
            return active === name ? "site-header__link is-active" : "site-header__link";
        }

        var pillHtml = pill
            ? '<span class="site-header__pill">' + esc(pill) + "</span>"
            : "";

        return (
            '<header class="site-header" role="banner">' +
            '<div class="site-header__inner">' +
            '<div class="site-header__left">' +
            '<a class="site-header__brand" href="' +
            esc(hub) +
            '">' +
            '<img src="' +
            esc(joinPrefix(prefix, "assets/logo.png")) +
            '" width="36" height="36" alt="">' +
            '<span>PLAY<span class="accent">NEXUS</span></span></a>' +
            pillHtml +
            "</div>" +
            '<nav class="site-header__nav" aria-label="Site">' +
            '<a class="' +
            cls("hub") +
            '" href="' +
            esc(hub) +
            '#home">Hub</a>' +
            '<a class="' +
            cls("games") +
            '" href="' +
            esc(games) +
            '">Games</a>' +
            '<a class="' +
            cls("apps") +
            '" href="' +
            esc(appsHash) +
            '">Apps</a>' +
            '<a class="' +
            cls("community") +
            '" href="' +
            esc(community) +
            '">Community</a>' +
            '<a class="' +
            cls("about") +
            '" href="' +
            esc(about) +
            '">About</a>' +
            "</nav>" +
            '<a class="site-header__hub-btn" href="' +
            esc(hub) +
            '#home"><span aria-hidden="true">←</span> Hub</a>' +
            "</div></header>"
        );
    }

    function footerHTML(prefix) {
        var hub = joinPrefix(prefix, "index.html");
        var games = joinPrefix(prefix, "games/games.html");
        var community = joinPrefix(prefix, "community/community.html");
        var about = joinPrefix(prefix, "about/about.html");
        var year = new Date().getFullYear();

        return (
            '<footer class="site-footer" role="contentinfo">' +
            '<div class="site-footer__inner">' +
            '<div>' +
            '<h2 class="site-footer__title">PLAYNEXUS</h2>' +
            "<p class=\"site-footer__text\">Auth-first hub for games, browser apps, and community—tuned for lightweight hosting on Render with Supabase PostgreSQL.</p>" +
            "</div>" +
            "<div>" +
            '<h2 class="site-footer__title">Explore</h2>' +
            '<ul class="site-footer__links">' +
            '<li><a href="' +
            esc(hub) +
            '#home">Command hub</a></li>' +
            '<li><a href="' +
            esc(games) +
            '">Play Center</a></li>' +
            '<li><a href="' +
            esc(hub) +
            '#apps">Apps roadmap</a></li>' +
            '<li><a href="' +
            esc(community) +
            '">Community</a></li>' +
            '<li><a href="' +
            esc(about) +
            '">About this site</a></li>' +
            "</ul></div>" +
            "<div>" +
            '<h2 class="site-footer__title">Build</h2>' +
            "<p class=\"site-footer__text\">Stack: FastAPI, vanilla JS, Flyway SQL. See <code>README.md</code> in the repository.</p>" +
            "</div></div>" +
            '<div class="site-footer__bar">© ' +
            year +
            " PlayNexus — experimental portal</div></footer>"
        );
    }

    function authFooterHTML(prefix) {
        var about = joinPrefix(prefix, "about/about.html");
        return (
            '<footer class="site-footer site-footer--auth" role="contentinfo">' +
            '<div class="site-footer__bar">' +
            '<a href="' +
            esc(about) +
            '" style="color:rgba(6,182,212,0.95);text-decoration:none;font-family:Outfit,sans-serif;font-size:0.8rem;">About this project</a>' +
            " · " +
            '<span style="opacity:0.5">PlayNexus</span>' +
            "</div></footer>"
        );
    }

    function init() {
        var prefix = document.body.getAttribute("data-root-prefix");
        if (prefix === null) {
            prefix = "..";
        }

        var active = document.body.getAttribute("data-chrome-active") || "";
        var pill = document.body.getAttribute("data-chrome-pill") || "";

        var h = document.getElementById("site-chrome-header");
        var f = document.getElementById("site-chrome-footer");
        if (h) {
            h.innerHTML = headerHTML(prefix, active, pill);
        }
        if (f) {
            f.innerHTML = footerHTML(prefix);
        }

        var hubF = document.getElementById("site-chrome-footer-hub");
        if (hubF) {
            hubF.innerHTML = footerHTML("");
        }

        var authF = document.getElementById("site-chrome-footer-auth");
        if (authF) {
            authF.innerHTML = authFooterHTML("");
        }
    }

    window.PlayNexusChrome = {
        init: init,
        headerHTML: headerHTML,
        footerHTML: footerHTML,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
