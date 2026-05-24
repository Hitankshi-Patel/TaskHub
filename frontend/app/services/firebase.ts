import { initializeApp, getApps, getApp, FirebaseApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, GithubAuthProvider, Auth, getRedirectResult } from 'firebase/auth';

// Loaded from client-side environment variables (.env.local)
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "mock-api-key",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "mock-auth-domain.firebaseapp.com",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "mock-project-id",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "mock-storage-bucket.appspot.com",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "123456789",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:123456789:web:12345"
};

// Check if real Firebase env variables are properly set (not mock values)
export const isFirebaseConfigured =
  !!process.env.NEXT_PUBLIC_FIREBASE_API_KEY &&
  process.env.NEXT_PUBLIC_FIREBASE_API_KEY !== "mock-api-key";

let app: FirebaseApp | undefined;
let auth: Auth | undefined;

const googleProvider = new GoogleAuthProvider();
googleProvider.addScope('email');
googleProvider.addScope('profile');

const githubProvider = new GithubAuthProvider();
githubProvider.addScope('user:email');

try {
  app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
  auth = getAuth(app);

  // Preemptively resolve any pending redirect result from previous sign-in attempts.
  // This MUST be caught here — if Google/GitHub providers are not enabled in Firebase
  // Console yet, the SDK throws `auth/operation-not-allowed` as an unhandled rejection
  // on every page load. By catching it here we prevent the console flood.
  if (auth) {
    getRedirectResult(auth).catch((err: Error & { code?: string }) => {
      if (err?.code === 'auth/operation-not-allowed') {
        console.warn(
          '[TaskHub] Firebase OAuth providers (Google/GitHub) are not yet enabled.\n' +
          'Go to Firebase Console → Authentication → Sign-in method and enable them.\n' +
          'You can use the Mock Login buttons in the meantime.'
        );
      }
      // All other redirect errors are silently swallowed here;
      // actual login button clicks will surface errors to the UI.
    });
  }
} catch (error) {
  console.warn('[TaskHub] Firebase client initialization failed. Mock login will be used.', error);
}

export { auth, googleProvider, githubProvider };
export default app;
