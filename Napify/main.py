import webview
import sys
import os

def block_keyboard_input(window):
    """
    Inject JavaScript to block all keyboard input in the webview window.
    """
    js = """
    document.addEventListener('keydown', function(e) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    }, true);
    document.addEventListener('keyup', function(e) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    }, true);
    document.addEventListener('keypress', function(e) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    }, true);
    """
    window.evaluate_js(js)

def main():
    # Get the directory of the current script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    animation_file = os.path.join(base_dir, 'animation', 'animation.html')

    # Create a window that is frameless and full screen
    window = webview.create_window(
        'Napify',
        animation_file,
        width=1920,  # We'll set to full screen size after getting screen dimensions
        height=1080,
      # hidden=True,
        frameless=True,
        easy_drag=False,
        resizable=False,
        fullscreen=True  # This might work on some platforms
    )

    # Alternatively, we can set the window to the screen size after getting it
    # But webview does not provide a direct way to get screen size, so we use fullscreen=True
    # and then adjust if needed.

    # Set the window to be always on top
    # Note: webview does not have a direct setting for always on top, but we can try to set it after creation
    # However, we'll rely on fullscreen and frameless to cover the screen.

    # Start the webview application
    webview.start(lambda w: block_keyboard_input(w), window, debug=False)

if __name__ == '__main__':
    main()