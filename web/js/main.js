document.addEventListener('DOMContentLoaded', () => {
  console.log('Application initialized');

  // Listen for recording events
  window.addEventListener('recordingStarted', (e) => {
    console.log('Recording started with stream:', e.detail);
  });

  window.addEventListener('recordingStopped', () => {
    console.log('Recording stopped');
  });
});