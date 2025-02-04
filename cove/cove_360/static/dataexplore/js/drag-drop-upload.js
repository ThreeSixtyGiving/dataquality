/* Requires drop-area div */
(function () {
  const dropArea = document.getElementsByTagName('body')[0];

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, e => {
      e.preventDefault();
      e.stopPropagation();

      if (eventName === 'dragenter' || eventName === 'dragover') {
        dropArea.classList.add('highlight');
      } else {
        dropArea.classList.remove('highlight');
      }

      if (eventName === 'drop') {
        const dt = e.dataTransfer;
        const files = dt.files;

        /* Currently we only support one file upload at a time */
        uploadFile(files[0]);
      }
    }, false);
  });

  function uploadFile (file) {
    const formData = new FormData();
    const csrftoken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

    formData.append('original_file', file);
    formData.append('csrfmiddlewaretoken', csrftoken);

    fetch('.', {
      method: 'POST',
      body: formData
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        window.location = response.url;
      })
      .catch(error => {
        console.error('Error uploading file:', error);
        alert('File upload failed');
      });
  }
})();
