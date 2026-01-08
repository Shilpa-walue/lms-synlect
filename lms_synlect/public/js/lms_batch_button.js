frappe.ready(() => {
    // Only run on batch pages
    if (!window.location.pathname.includes("/batches/")) return;

    const interval = setInterval(() => {
        // Try multiple possible selectors for LMS batch page
        const actionContainer =
            document.querySelector(".batch-header-actions") ||
            document.querySelector(".page-actions") ||
            document.querySelector(".batch-details .actions") ||
            document.querySelector(".batch-hero .actions") ||
            document.querySelector(".container .d-flex.justify-content-between") ||
            document.querySelector(".batch-header");

        if (!actionContainer) return;

        clearInterval(interval);

        // Prevent duplicate button
        if (document.getElementById("vr-class-btn")) return;

        const btn = document.createElement("button");
        btn.id = "vr-class-btn";
        btn.className = "btn btn-primary btn-sm ml-2";
        btn.innerText = "Live VR Class";
        btn.style.marginLeft = "10px";

        btn.onclick = () => {
            // Get the batch name from the URL path
            const pathParts = window.location.pathname.split("/");
            const batchIndex = pathParts.indexOf("batches");
            const batchName = batchIndex !== -1 ? pathParts[batchIndex + 1] : "";

            // Redirect to VR class URL
            const vrClassUrl = "https://synlect-lms.m.frappe.cloud/streaming";
            window.open(vrClassUrl, "_blank");
        };

        actionContainer.appendChild(btn);
    }, 500);
});
