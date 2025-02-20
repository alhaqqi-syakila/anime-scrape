document.addEventListener("DOMContentLoaded", function () {
    const paginationContainer = document.getElementById("pagination-numbers");
    if (!paginationContainer) return;

    const pageNumbers = [...paginationContainer.children]; // Semua elemen halaman
    const maxVisible = 5; // Maksimal 5 halaman yang terlihat sekaligus

    function updatePagination(currentPage) {
        let visiblePages = [];
        let leftDots = false;
        let rightDots = false;

        for (let i = 0; i < pageNumbers.length; i++) {
            const pageNum = parseInt(pageNumbers[i].dataset.page);
            if (pageNum === 1 || pageNum === lastPage || 
                (pageNum >= currentPage - 2 && pageNum <= currentPage + 2)) {
                visiblePages.push(pageNumbers[i]);
            } else if (pageNum < currentPage - 2 && !leftDots) {
                leftDots = true;
            } else if (pageNum > currentPage + 2 && !rightDots) {
                rightDots = true;
            }
        }

        paginationContainer.innerHTML = ""; // Kosongkan pagination

        if (leftDots) {
            paginationContainer.appendChild(pageNumbers[0]); // Tambahkan halaman pertama
            paginationContainer.innerHTML += '<span class="page-dots">...</span>'; // Tambahkan titik
        }

        visiblePages.forEach(page => paginationContainer.appendChild(page));

        if (rightDots) {
            paginationContainer.innerHTML += '<span class="page-dots">...</span>'; // Tambahkan titik
            paginationContainer.appendChild(pageNumbers[pageNumbers.length - 1]); // Tambahkan halaman terakhir
        }
    }

    const currentPage = parseInt(document.querySelector(".page-number.active")?.dataset.page || "1");
    updatePagination(currentPage);
});
