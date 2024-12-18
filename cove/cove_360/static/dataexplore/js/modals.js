(function () {
  /* Add handler to launch modals  */
  for (const modalOpenBtn of document.querySelectorAll('button[data-toggle="modal"]')) {
    modalOpenBtn.addEventListener('click', (event) => {
      /* Not sure why these are done by class */
      const modal = document.getElementsByClassName(event.target.dataset.targetClass);
      modal[0].removeAttribute('aria-hidden');
      modal[0].classList.add('modal--shown');
    });
  }

  /* Add handler to close modals */
  for (const modalCloseBtn of document.getElementsByClassName('modal__close')) {
    modalCloseBtn.addEventListener('click', (event) => {
      const modal = event.target.parentElement.parentElement;
      modal.classList.remove('modal--shown');
      modal.setAttribute('aria-hidden', true);
    });
  }
})();
