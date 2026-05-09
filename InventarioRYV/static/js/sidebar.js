/**
 * Manejo del sidebar responsivo
 * Toggle para mostrar/ocultar el menú en pantallas pequeñas
 */

(function() {
    const sidebarMenu = document.getElementById('sidebar-menu');
    const sidebarToggle = document.getElementById('sidebar-toggle');

    // Solo inicializar si existen los elementos
    if (!sidebarMenu || !sidebarToggle) {
        return;
    }

    // Toggle del sidebar
    sidebarToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        sidebarMenu.classList.toggle('active');
        sidebarToggle.setAttribute('aria-expanded', 
            sidebarToggle.getAttribute('aria-expanded') === 'true' ? 'false' : 'true'
        );
    });

    // Cerrar sidebar al hacer click en un enlace
    const sidebarLinks = sidebarMenu.querySelectorAll('a');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            sidebarMenu.classList.remove('active');
            sidebarToggle.setAttribute('aria-expanded', 'false');
        });
    });

    // Cerrar sidebar si se hace click fuera de él
    document.addEventListener('click', function(e) {
        const isClickInsideSidebar = sidebarMenu.contains(e.target);
        const isClickInsideToggle = sidebarToggle.contains(e.target);

        if (!isClickInsideSidebar && !isClickInsideToggle && sidebarMenu.classList.contains('active')) {
            sidebarMenu.classList.remove('active');
            sidebarToggle.setAttribute('aria-expanded', 'false');
        }
    });

    // Cerrar sidebar al cambiar el tamaño de la pantalla a desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            sidebarMenu.classList.remove('active');
            sidebarToggle.setAttribute('aria-expanded', 'false');
        }
    });
})();
