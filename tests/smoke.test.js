/**
 * PlayNexus API Smoke Test (Lightweight)
 *
 * Purpose:
 * Performs a full authentication lifecycle (Signup -> Login -> Fetch -> Delete)
 * using native Node.js fetch to ensure the backend endpoints are live.
 */

(async () => {
  let url = process.env.SITE_URL;
  if (!url || url === 'null' || url === 'undefined') {
    const env = process.env.APP_ENV || 'staging';
    url = (env === 'production') ? 'https://playnexus-prod.onrender.com' : 'https://playnexus-test.onrender.com';
  }

  if (!url.startsWith('http')) url = 'http://127.0.0.1:8000';

  console.log(`🔍 Starting Lightweight API Smoke Test against: ${url}`);
  
  const dummyUser = `test_runner_${Date.now()}`;
  const dummyPass = `P@ssword123!`;

  try {
    // 1. SIGNUP
    console.log(`👤 Creating test account: ${dummyUser}...`);
    let res = await fetch(`${url}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: dummyUser, password: dummyPass, confirm_password: dummyPass })
    });
    if (!res.ok) throw new Error(`Signup failed: ${await res.text()}`);
    console.log('✅ Signup successful.');

    // 2. LOGIN
    console.log(`🔑 Logging into test account...`);
    res = await fetch(`${url}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: dummyUser, password: dummyPass })
    });
    if (!res.ok) throw new Error(`Login failed: ${await res.text()}`);
    console.log('✅ Login successful.');

    // 3. CHECK ENDPOINT STATUS
    console.log(`📡 Checking user endpoint status...`);
    res = await fetch(`${url}/api/auth/me?username=${dummyUser}`);
    if (!res.ok) throw new Error(`Status check failed: ${await res.text()}`);
    console.log('✅ Active user profile state verified.');

    // 4. DELETE ACCOUNT (CLEANUP)
    console.log(`🧨 Deleting dummy account (Cleanup)...`);
    res = await fetch(`${url}/api/auth/account`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: dummyUser, password: dummyPass })
    });
    if (!res.ok) throw new Error(`Delete failed: ${await res.text()}`);
    console.log('✅ Account successfully deleted. CLEANUP COMPLETE.');

    console.log("🎉 ALL ENDPOINTS ACTIVE AND HEALTHY.");

  } catch (error) {
    console.error("❌ ERROR during smoke test:", error.message);
    process.exit(1);
  }
})();