# Firebase setup and account behavior

The Streamlit app uses Firebase Authentication and Cloud Firestore REST APIs. It sends each user's Firebase ID token to Firestore, so the deployed Firestore Security Rules enforce account ownership. No Firebase Admin service account is needed.

## Configuration

The supplied Firebase project configuration is saved in the local ignored .env file. The Python app uses FIREBASE_API_KEY and FIREBASE_PROJECT_ID. The other supplied web-app settings are retained for future browser integrations. Analytics is not initialized, and Cloud Storage is not used.

Do not overwrite an existing .env when following the first-time setup instructions. Set GROQ_API_KEY there to enable concepts, quizzes, and tutor replies. Firebase login and saved data do not require a Groq key. Restart Streamlit after changing environment settings.

For deployment, copy the environment settings into Streamlit app secrets. Do not upload .env to Git.

## Required Firebase Console settings

1. Authentication: enable Email/Password.
2. Firestore: create the default database, using Standard edition / Native mode.
3. Firestore Rules: publish the complete contents of firestore.rules from this repository.

The rules grant access only when the authenticated UID matches the UID in the document path. They also restrict fields and sizes. Do not use allow read, write: if true.

If you already have the Firebase CLI installed and are authenticated as the project owner, you can alternatively publish with:

    firebase deploy --only firestore:rules --project papersensei-ba4b3

This command is an alternative to publishing through the console, not a step the app runs automatically.

## Account and storage flow

Create an account or sign in on the welcome screen. Guest preview remains available and does not save to Firebase. Login tokens remain in the server's per-browser Streamlit session; passwords are not stored in Firestore. Tokens renew during an active session. Reopening the app may require another login, after which My saved sessions restores prior work.

Documents, generated questions, answers, topic performance, paper analysis, and tutor conversations save automatically for signed-in users. Save now explicitly retries saving. The interface shows an error if saving fails and keeps local work available. Sign out and Reset session first attempt to save. Discarding unsaved changes requires the explicitly labeled action.

Loading new notes starts a new saved session after saving the previous one. Reset starts a new blank session and preserves existing cloud sessions. Session titles can be edited in the sidebar. My saved sessions displays 20 records at a time with a Load more action.

Firestore paths:

    users/{uid}/study_sessions/{session_id}
        title
        payload             JSON snapshot of study, papers, and insights
        updated_at          UTC timestamp
        schema_version      1

    users/{uid}/study_sessions/{session_id}/messages/{message_id}
        role
        content
        created_at          UTC timestamp

Messages are separate records with stable IDs, so save retries do not duplicate them. Quiz state is a versioned JSON snapshot capped at 750,000 UTF-8 bytes to remain below Firestore's document limit. Save failures never silently truncate data. The app uses Firestore update-time preconditions to detect edits from other tabs; you can save a conflicting version as a new session or explicitly reload the saved version.

Tutor chat uses the current source and up to 12 recent messages, bounded to 12,000 characters. Older conversation history remains saved but is not all sent to Groq. A failed tutor response retains the user's question and offers Retry tutor reply.

## Verification

Offline tests:

    .venv/Scripts/python -m pytest -q

Optional live Firebase check:

    .venv/Scripts/python scripts/check_firebase.py --live

The live check creates two temporary accounts, saves a sample session and two messages, verifies restore/list/token refresh, tests unauthenticated and cross-account access, and deletes the created data and accounts. It sends no email. Any cleanup failure is reported.

## Current boundaries

Task 2 extraction is unchanged and remains pending. No raw PDFs are stored. Chroma, Google login, browser-persistent login cookies, and account deletion are not implemented. This version stores learning progress per study session, rather than calculating lifetime performance across sessions.
