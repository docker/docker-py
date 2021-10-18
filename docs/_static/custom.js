$(document).ready(function() {
    var nav = document.querySelector('div.sphinxsidebar ul');
    nav.style.height = 'auto'; // to get actual height
    var height = $(nav).height() + 'px';
    var updateHeight = function() {
        nav.style.height = ''; // to get scroll height
        if (nav.offsetHeight >= nav.scrollHeight) {
            nav.style.height = height;  // no scrollbar, use actual height
        }
    };
    updateHeight();
    $(window).resize(updateHeight);
});
