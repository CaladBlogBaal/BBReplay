function addFlashListenerAll(buttonID) {
    document.querySelectorAll(buttonID).forEach(element => {
        element.addEventListener('click', function() {
        const button = this;

        // Remove any existing flash effect
        button.classList.remove('flash', 'fade-out');

        setTimeout(() => {
            button.classList.add('flash');
        }, 0);

        setTimeout(() => {
            button.classList.add('fade-out');
        }, 100);

        // Remove the classes after the animation is done
        setTimeout(() => {
            button.classList.remove('flash', 'fade-out');
        }, 600); // Adjust this time to match the duration of the fade-out
        });
    });
}

addFlashListenerAll('.custom-button');
addFlashListenerAll('.button');