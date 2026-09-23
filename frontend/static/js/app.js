(function () {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const fileList = document.getElementById("fileList");
  const submitBtn = document.getElementById("submitBtn");
  if (!dropzone || !fileInput) return;

  function render() {
    const files = Array.from(fileInput.files || []);
    fileList.innerHTML = "";
    files.forEach((f) => {
      const li = document.createElement("li");
      li.className = "filechip";
      const name = document.createElement("span");
      name.className = "fname";
      name.textContent = f.name;
      const size = document.createElement("span");
      size.className = "fsize";
      size.textContent = (f.size / 1024).toFixed(0) + " KB";
      li.append(name, size);
      fileList.appendChild(li);
    });
    submitBtn.disabled = files.length === 0;
  }

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") fileInput.click();
  });
  fileInput.addEventListener("change", render);

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("drag");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("drag");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      render();
    }
  });
})();
