// dashboard/static/dashboard/js/kyc.js

document.addEventListener("DOMContentLoaded", function () {
  const profilePicInput = document.querySelector('input[name="profile_pic"]');
  const docInput = document.querySelector('input[name="kyc_doc"]');

  // preview container
  const profilePreview = document.createElement("div");
  profilePreview.className = "preview-image";
  profilePicInput?.insertAdjacentElement("afterend", profilePreview);

  function previewImage(input, container) {
    container.innerHTML = "";
    const file = input.files[0];
    if (file && file.type.startsWith("image/")) {
      const img = document.createElement("img");
      img.className = "kyc-doc-img";
      img.src = URL.createObjectURL(file);
      container.appendChild(img);
    } else if (file) {
      container.textContent = `📄 Selected File: ${file.name}`;
    }
  }

  profilePicInput?.addEventListener("change", () =>
    previewImage(profilePicInput, profilePreview)
  );

  if (docInput) {
    const docPreview = document.createElement("p");
    docPreview.className = "file-preview";
    docInput.insertAdjacentElement("afterend", docPreview);
    docInput.addEventListener("change", () => {
      const file = docInput.files[0];
      docPreview.textContent = file
        ? `📄 Selected File: ${file.name}`
        : "";
    });
  }
});
