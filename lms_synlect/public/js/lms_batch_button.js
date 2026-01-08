frappe.ready(() => {
    const interval = setInterval(() => {
        // LMS batch action header (exists only on batch detail page)
        const actionContainer = document.querySelector(".batch-header-actions");

        if (!actionContainer) return;

        clearInterval(interval);

        // Prevent duplicate button
        if (document.getElementById("vr-class-btn")) return;

        const btn = document.createElement("button");
        btn.id = "vr-class-btn";
        btn.className = "btn btn-primary btn-sm";
        btn.innerText = "Live VR Class";

        btn.onclick = () => {
            // Get the batch name from the route
            const batchName = frappe.get_route()[2];

            // Option 1: Redirect to custom VR URL directly
            // Replace this URL with your actual VR class URL
           const vrClassUrl = "https://synlect-lms.m.frappe.cloud/streaming";
            // const vrClassUrl = "https://your-vr-platform.com/class/" + encodeURIComponent(batchName);
            window.open(vrClassUrl, "_blank");

            // Option 2: If you need to call a backend API first to get the URL
            // Uncomment below and comment out the above
            /*
            frappe.call({
                method: "lms_synlect.api.get_vr_class_url",
                args: {
                    batch: batchName
                },
                freeze: true,
                freeze_message: "Loading VR Class...",
                callback: function(r) {
                    if (r.message && r.message.url) {
                        window.open(r.message.url, "_blank");
                    } else {
                        frappe.msgprint("VR Class URL not configured for this batch.");
                    }
                }
            });
            */
        };

        actionContainer.appendChild(btn);
    }, 400);
});
