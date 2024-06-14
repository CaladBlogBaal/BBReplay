// Wait for the DOMContentLoaded event
document.addEventListener('DOMContentLoaded', function() {
        const fileInput = document.getElementById('files');
        const submitButton = document.getElementById('submitButton');
        // Get the upload link element and add a click event listener
        document.getElementById('uploadLink').addEventListener('click', function(event) {
        // Prevent the default link behavior
        event.preventDefault();

        // Check if the current window location is not already at the target route
        if (window.location.pathname !== '/upload') {
            window.location.href = '/upload';
        }

        // Display the file upload form
        // document.getElementById('fileUploadForm').style.display = 'block';

        // Simulate a click on the file input element to trigger the file selection dialog
        document.querySelector('input[name="files"]').click();
        // Listen for keypress event on file input
        fileInput.addEventListener('keypress', function(event) {
            // Check if the key pressed is Enter (keyCode 13)
            if (event.key === 'Enter') {
                // Simulate a click on the submit button
                submitButton.click();
            }
        });
    });
});