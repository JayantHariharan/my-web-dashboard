/* ─── main.js — PlayNexus interactions ─── */

/* ══ Navbar scroll effect ══ */
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 40);
}, { passive: true });

/* ══ Hamburger mobile menu ══ */
const hamburger = document.getElementById('hamburger-btn');
const navLinks  = document.querySelector('.nav-links');

hamburger.addEventListener('click', () => {
  const isOpen = navLinks.classList.toggle('mobile-open');
  hamburger.classList.toggle('open', isOpen);
  hamburger.setAttribute('aria-expanded', isOpen);
});

// Close mobile menu when a link is clicked
navLinks.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    navLinks.classList.remove('mobile-open');
    hamburger.classList.remove('open');
    hamburger.setAttribute('aria-expanded', false);
  });
});

/* ══ Scroll-reveal (IntersectionObserver) ══ */
const reveals = document.querySelectorAll(
  '.feature-card, .showcase-card, .about-text, .about-visual, .cta-card, .pipeline-step'
);
reveals.forEach(el => el.classList.add('reveal'));

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      // stagger children in the same parent
      const siblings = [...entry.target.parentElement.querySelectorAll('.reveal')];
      const idx = siblings.indexOf(entry.target);
      entry.target.style.transitionDelay = `${idx * 80}ms`;
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

reveals.forEach(el => revealObserver.observe(el));

/* ══ Animated counters in hero ══ */
function animateCounter(el) {
  const target   = +el.dataset.target;
  const duration = 1800; // ms
  const step     = 16;   // ~60fps
  const increment = target / (duration / step);
  let current = 0;

  const timer = setInterval(() => {
    current += increment;
    if (current >= target) {
      current = target;
      clearInterval(timer);
    }
    el.textContent = Math.floor(current);
  }, step);
}

const statNums = document.querySelectorAll('.stat-num');
const statsObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      animateCounter(entry.target);
      statsObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.5 });

statNums.forEach(el => statsObserver.observe(el));

/* ══ Active nav link on scroll ══ */
const sections = document.querySelectorAll('section[id]');
const navLinkEls = document.querySelectorAll('.nav-link:not(.nav-cta)');

const sectionObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      navLinkEls.forEach(link => {
        const active = link.getAttribute('href') === `#${entry.target.id}`;
        link.style.color = active ? 'var(--text-primary)' : '';
        link.style.background = active ? 'var(--bg-card)' : '';
      });
    }
  });
}, { rootMargin: '-40% 0px -55% 0px' });

sections.forEach(s => sectionObserver.observe(s));

/* ══ Feature card tilt on mouse move ══ */
document.querySelectorAll('.feature-card').forEach(card => {
  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width  - 0.5;
    const y = (e.clientY - rect.top)  / rect.height - 0.5;
    card.style.transform = `translateY(-4px) rotateX(${-y * 6}deg) rotateY(${x * 6}deg)`;
  });
  card.addEventListener('mouseleave', () => {
    card.style.transform = '';
  });
});

/* ══ Typing cursor effect on hero title ══ */
// subtle gradient shift on mouse move across hero
const hero = document.getElementById('hero');
hero.addEventListener('mousemove', (e) => {
  const x = (e.clientX / window.innerWidth)  * 100;
  const y = (e.clientY / window.innerHeight) * 100;
  hero.querySelector('.orb-1').style.transform =
    `translate(${x * 0.08}px, ${y * 0.08}px)`;
  hero.querySelector('.orb-2').style.transform =
    `translate(${-x * 0.05}px, ${-y * 0.05}px)`;
}, { passive: true });

console.log('%c🚀 PlayNexus', 'font-size:20px;color:#818cf8;font-weight:bold;');
console.log('%cBuilt with ❤️  · Deployed via GitHub Actions', 'color:#94a3b8;');
