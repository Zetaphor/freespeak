document.addEventListener('DOMContentLoaded', () => {
  console.log('Application initialized');

  // Create audio elements for feedback sounds
  const activateSound = new Audio('audio/activate.ogg');
  const deactivateSound = new Audio('audio/deactivate.ogg');

  // Listen for recording events
  window.addEventListener('recordingStarted', (e) => {
    console.log('Recording started with stream:', e.detail);
    activateSound.play().catch(error => console.error("Error playing activate sound:", error));
  });

  window.addEventListener('recordingStopped', () => {
    console.log('Recording stopped');
    deactivateSound.play().catch(error => console.error("Error playing deactivate sound:", error));
  });
});