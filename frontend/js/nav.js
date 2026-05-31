const navLogoutButton = document.querySelector("#navLogoutButton");
const navLinks = document.querySelectorAll(".side-nav-link");

function clearNavSession() {
  localStorage.removeItem("bingo_access_token");
  localStorage.removeItem("bingo_user");
  window.location.href = "./login.html";
}

function markCurrentNavLink() {
  const currentPage = window.location.pathname.split("/").pop();

  navLinks.forEach((link) => {
    const linkPage = link.getAttribute("href")?.split("/").pop();
    link.classList.toggle("is-active", linkPage === currentPage);
  });
}

if (navLogoutButton) {
  navLogoutButton.addEventListener("click", clearNavSession);
}

markCurrentNavLink();
