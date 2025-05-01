document.addEventListener('DOMContentLoaded', function () {
    const about = document.querySelector('.about');
    const semiCircle = document.getElementById('semiCircle');
    const blackOverlay = document.getElementById('blackOverlay');
    const contentOnBlack = document.getElementById('contentOnBlack');

    about.addEventListener('mouseenter', function () {
        semiCircle.style.transform = 'scale(1)';
        semiCircle.style.opacity = '1';
        blackOverlay.style.opacity = '1';
        blackOverlay.classList.add('active');
    });

    about.addEventListener('mouseleave', function () {
        semiCircle.style.transform = 'scale(0)';
        semiCircle.style.opacity = '0';
        blackOverlay.style.opacity = '0';
        blackOverlay.classList.remove('active');
    });

    const collageButton = document.getElementById('collageButton');
    const closeButton = document.getElementById('closeButton');
    const window = document.getElementById('window');
    const typingText = document.querySelector('.window-top-text');

    // Открытие окна
    collageButton.addEventListener('click', function () {
        window.classList.add('open');
        collageButton.style.display = 'none'; // Скрываем кнопку "collage it"
        typingText.style.animation = 'none'; // Сбрасываем анимацию
        setTimeout(() => {
            typingText.style.animation = 'appear-from-shadow 2s ease-out forwards'; // Запускаем анимацию
        }, 350); // Небольшая задержка для сброса анимации
    });

    // Закрытие окна
    closeButton.addEventListener('click', function () {
        window.classList.remove('open');
        setTimeout(() => {
            collageButton.style.display = 'flex'; // Показываем кнопку "collage it" после анимации
        }, 0); // Задержка для завершения анимации
    });
});