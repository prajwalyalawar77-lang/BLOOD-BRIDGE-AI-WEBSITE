<script>

/* =====================================================
   BLOODBRIDGE AI - COMPLETE JAVASCRIPT
===================================================== */


/* =====================================================
   1. JOIN THE NETWORK MODAL
===================================================== */

function openNetworkForm() {

    const modal =
        document.getElementById("networkModal");

    modal.classList.add("active");

}


function closeNetworkForm() {

    const modal =
        document.getElementById("networkModal");

    modal.classList.remove("active");

}


/* Close modal when clicking outside */

window.addEventListener("click", function(event) {

    const modal =
        document.getElementById("networkModal");

    if (event.target === modal) {

        closeNetworkForm();

    }

});



/* =====================================================
   2. LOAD BLOOD AVAILABILITY
===================================================== */

async function loadBloodAvailability() {

    const grid =
        document.getElementById(
            "bloodAvailabilityGrid"
        );


    if (!grid) {

        return;

    }


    grid.innerHTML = `

        <div class="loading-card">

            🔄 Loading live blood availability...

        </div>

    `;


    try {

        const response =
            await fetch(
                "/blood-availability"
            );


        if (!response.ok) {

            throw new Error(
                "Server response error"
            );

        }


        const data =
            await response.json();


        if (
            !data.success ||
            !data.results ||
            data.results.length === 0
        ) {

            grid.innerHTML = `

                <div class="loading-card">

                    🩸 No blood availability
                    has been added yet.

                    <br><br>

                    Click
                    <strong>JOIN THE NETWORK</strong>
                    to add blood availability.

                </div>

            `;

            return;

        }


        grid.innerHTML = "";


        data.results.forEach(function(blood) {


            let statusClass =
                "available";


            if (blood.status === "Critical") {

                statusClass = "critical";

            }

            else if (
                blood.status === "Low Stock"
            ) {

                statusClass = "low";

            }


            const card = document.createElement(
                "div"
            );

            card.className =
                `blood-card ${statusClass}`;


            card.innerHTML = `

                <div class="blood-card-top">

                    <div class="blood-type">

                        ${escapeHTML(
                            blood.blood_group
                        )}

                    </div>

                    <span class="status-dot"></span>

                </div>


                <div class="blood-info">

                    <h3>

                        ${escapeHTML(
                            String(blood.units)
                        )}

                        Units

                    </h3>


                    <p>

                        ${escapeHTML(
                            blood.status
                        )}

                    </p>


                    <div class="blood-location">

                        📍
                        ${escapeHTML(
                            blood.location
                        )}

                    </div>


                    <small>

                        ${escapeHTML(
                            blood.provider_type
                        )}

                        •
                        
                        ${escapeHTML(
                            blood.name
                        )}

                    </small>

                </div>

            `;


            grid.appendChild(card);

        });

    }


    catch (error) {

        console.error(
            "Blood availability error:",
            error
        );


        grid.innerHTML = `

            <div class="loading-card">

                ⚠️ Unable to load blood
                availability.

                <br><br>

                Please make sure Flask
                is running.

            </div>

        `;

    }

}



/* =====================================================
   3. FIND BLOOD
===================================================== */

async function findBlood() {


    const bloodGroup =
        document.getElementById(
            "bloodGroup"
        ).value;


    const location =
        document.getElementById(
            "location"
        ).value.trim();


    const priority =
        document.getElementById(
            "priority"
        ).value;


    const button =
        document.getElementById(
            "findBloodBtn"
        );


    const results =
        document.getElementById(
            "bloodResults"
        );



    /* ---------------------------------------------
       VALIDATION
    --------------------------------------------- */


    if (!bloodGroup) {

        showMessage(
            results,
            "🩸 Please select a blood group."
        );

        return;

    }


    if (!location) {

        showMessage(
            results,
            "📍 Please enter your location."
        );

        return;

    }


    if (!priority) {

        showMessage(
            results,
            "🚨 Please select emergency priority."
        );

        return;

    }



    /* ---------------------------------------------
       SEARCHING
    --------------------------------------------- */

    button.disabled = true;

    button.innerHTML =
        "🔎 SEARCHING...";


    results.innerHTML = `

        <div class="no-result">

            🔎 Searching BloodBridge network...

            <br>

            Finding ${escapeHTML(bloodGroup)}
            blood near
            ${escapeHTML(location)}...

        </div>

    `;



    try {


        const response =
            await fetch(
                "/find-blood",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            blood_group:
                                bloodGroup,

                            location:
                                location,

                            priority:
                                priority

                        })

                }
            );


        if (!response.ok) {

            throw new Error(
                "Search request failed"
            );

        }


        const data =
            await response.json();



        /* -----------------------------------------
           NO RESULTS
        ----------------------------------------- */

        if (
            !data.success ||
            !data.results ||
            data.results.length === 0
        ) {

            results.innerHTML = `

                <div class="no-result">

                    <h3>

                        🩸 No Matching Blood Found

                    </h3>


                    <p>

                        No ${escapeHTML(
                            bloodGroup
                        )}

                        blood is currently
                        available in the network.

                    </p>


                    <p>

                        You can try another
                        location or join the
                        network.

                    </p>

                </div>

            `;

            return;

        }



        /* -----------------------------------------
           RESULTS
        ----------------------------------------- */

        let html = `

            <div class="results-header">

                <span class="small-label">

                    MATCH FOUND

                </span>


                <h3>

                    🩸 Available Blood Sources

                </h3>


                <p>

                    ${data.results.length}
                    matching source(s) found

                </p>

            </div>


            <div class="result-grid">

        `;



        data.results.forEach(function(result) {


            let statusClass =
                "available";


            if (
                result.status ===
                "Critical"
            ) {

                statusClass =
                    "critical";

            }

            else if (
                result.status ===
                "Low Stock"
            ) {

                statusClass =
                    "low-stock";

            }



            html += `

                <div class="result-card">


                    <div class="result-blood">

                        ${escapeHTML(
                            result.blood_group
                        )}

                    </div>


                    <div class="result-details">


                        <h4>

                            ${escapeHTML(
                                result.name
                            )}

                        </h4>


                        <p>

                            🩸
                            <strong>
                                ${escapeHTML(
                                    String(
                                        result.units
                                    )
                                )}
                            </strong>

                            Units Available

                        </p>


                        <p>

                            📍
                            ${escapeHTML(
                                result.location
                            )}

                        </p>


                        <p>

                            🏥
                            ${escapeHTML(
                                result.provider_type
                            )}

                        </p>


                        <span
                            class="result-status
                            ${statusClass}">

                            ${escapeHTML(
                                result.status
                            )}

                        </span>


                        <br><br>


                        <button
                            type="button"
                            class="request-btn"

                            onclick="requestBlood(
                                ${result.id},
                                '${escapeJS(
                                    result.blood_group
                                )}',
                                '${escapeJS(
                                    result.name
                                )}',
                                '${escapeJS(
                                    result.location
                                )}',
                                '${escapeJS(
                                    result.phone
                                )}',
                                '${escapeJS(
                                    priority
                                )}'
                            )">

                            🚨 REQUEST BLOOD

                        </button>


                    </div>


                </div>

            `;

        });


        html += `

            </div>

        `;


        results.innerHTML = html;

    }


    catch (error) {

        console.error(
            "Find blood error:",
            error
        );


        results.innerHTML = `

            <div class="no-result">

                <h3>

                    ⚠️ Server Connection Error

                </h3>


                <p>

                    Unable to search the
                    BloodBridge network.

                </p>


                <p>

                    Please make sure
                    <strong>app.py</strong>
                    is running.

                </p>

            </div>

        `;

    }


    finally {

        button.disabled = false;

        button.innerHTML =
            "🔎 FIND BLOOD";

    }

}



/* =====================================================
   4. JOIN NETWORK FORM
===================================================== */

async function submitBloodAvailability(event) {


    event.preventDefault();


    const message =
        document.getElementById(
            "networkMessage"
        );


    const submitButton =
        event.target.querySelector(
            ".network-submit"
        );



    /* ---------------------------------------------
       GET FORM DATA
    --------------------------------------------- */

    const name =
        document.getElementById(
            "networkName"
        ).value.trim();


    const providerType =
        document.getElementById(
            "providerType"
        ).value;


    const bloodGroup =
        document.getElementById(
            "networkBloodGroup"
        ).value;


    const units =
        document.getElementById(
            "networkUnits"
        ).value;


    const location =
        document.getElementById(
            "networkLocation"
        ).value.trim();


    const phone =
        document.getElementById(
            "networkPhone"
        ).value.trim();



    /* ---------------------------------------------
       VALIDATION
    --------------------------------------------- */

    if (!name) {

        message.innerHTML =
            "⚠️ Please enter name or organization.";

        return;

    }


    if (!providerType) {

        message.innerHTML =
            "⚠️ Please select provider type.";

        return;

    }


    if (!bloodGroup) {

        message.innerHTML =
            "⚠️ Please select blood group.";

        return;

    }


    if (!units || Number(units) <= 0) {

        message.innerHTML =
            "⚠️ Please enter valid units.";

        return;

    }


    if (!location) {

        message.innerHTML =
            "⚠️ Please enter location.";

        return;

    }


    if (!phone) {

        message.innerHTML =
            "⚠️ Please enter contact number.";

        return;

    }



    /* ---------------------------------------------
       SEND TO FLASK
    --------------------------------------------- */

    submitButton.disabled = true;

    submitButton.innerHTML =
        "⏳ ADDING...";


    message.innerHTML =
        "Connecting to BloodBridge network...";


    try {


        const response =
            await fetch(
                "/add-blood",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            name:
                                name,

                            blood_group:
                                bloodGroup,

                            units:
                                Number(units),

                            location:
                                location,

                            phone:
                                phone,

                            provider_type:
                                providerType

                        })

                }
            );


        if (!response.ok) {

            throw new Error(
                "Server error"
            );

        }


        const data =
            await response.json();



        /* -----------------------------------------
           SUCCESS
        ----------------------------------------- */

        if (data.success) {


            message.innerHTML = `

                <span class="success-message">

                    ✅ Blood availability added
                    successfully!

                    <br>

                    ${bloodGroup}
                    •
                    ${units} units
                    •
                    ${location}

                </span>

            `;


            /*
             * Refresh dashboard
             */

            await loadBloodAvailability();


            /*
             * Clear form
             */

            document
                .getElementById(
                    "bloodAvailabilityForm"
                )
                .reset();



            /*
             * Close after success
             */

            setTimeout(function() {

                closeNetworkForm();

                message.innerHTML = "";

            }, 2000);

        }


        /* -----------------------------------------
           ERROR FROM FLASK
        ----------------------------------------- */

        else {

            message.innerHTML = `

                <span class="error-message">

                    ⚠️
                    ${escapeHTML(
                        data.message ||
                        "Unable to add availability."
                    )}

                </span>

            `;

        }

    }


    catch (error) {

        console.error(
            "Add blood error:",
            error
        );


        message.innerHTML = `

            <span class="error-message">

                ❌ Unable to connect to
                BloodBridge server.

                <br><br>

                Make sure
                <strong>python app.py</strong>
                is running.

            </span>

        `;

    }


    finally {

        submitButton.disabled = false;

        submitButton.innerHTML =
            "🩸 ADD BLOOD AVAILABILITY";

    }

}



/* =====================================================
   5. REQUEST BLOOD
===================================================== */

async function requestBlood(
    bloodId,
    bloodGroup,
    bankName,
    location,
    phone,
    priority
) {


    const confirmed =
        confirm(

            "Request " +
            bloodGroup +
            " blood from " +
            bankName +
            " at " +
            location +
            "?"

        );


    if (!confirmed) {

        return;

    }


    try {


        const response =
            await fetch(
                "/request-blood",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            blood_id:
                                bloodId,

                            blood_group:
                                bloodGroup,

                            bank_name:
                                bankName,

                            location:
                                location,

                            phone:
                                phone,

                            priority:
                                priority

                        })

                }
            );


        /*
         * The request-blood backend will be
         * added in the next stage.
         */

        if (response.status === 404) {

            alert(

                "🩸 Blood source selected!\n\n" +

                "Provider: " +
                bankName +
                "\n" +

                "Blood Group: " +
                bloodGroup +
                "\n" +

                "Location: " +
                location +
                "\n" +

                "Contact: " +
                phone

            );

            return;

        }


        const data =
            await response.json();


        if (data.success) {

            alert(
                "✅ Blood request sent successfully!"
            );

        }

        else {

            alert(

                "⚠️ " +
                (
                    data.message ||
                    "Unable to send request."
                )

            );

        }

    }


    catch (error) {

        console.error(
            "Request blood error:",
            error
        );


        /*
         * For now show provider details.
         */

        alert(

            "🩸 Blood source selected!\n\n" +

            "Provider: " +
            bankName +
            "\n" +

            "Blood Group: " +
            bloodGroup +
            "\n" +

            "Location: " +
            location +
            "\n" +

            "Contact: " +
            phone

        );

    }

}



/* =====================================================
   6. HELPER - SHOW MESSAGE
===================================================== */

function showMessage(element, message) {


    element.innerHTML = `

        <div class="no-result">

            ${message}

        </div>

    `;

}



/* =====================================================
   7. SECURITY - ESCAPE HTML
===================================================== */

function escapeHTML(value) {

    if (value === null ||
        value === undefined) {

        return "";

    }


    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}



/* =====================================================
   8. ESCAPE JAVASCRIPT STRINGS
===================================================== */

function escapeJS(value) {

    if (value === null ||
        value === undefined) {

        return "";

    }


    return String(value)
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, "\\n")
        .replace(/\r/g, "\\r");

}



/* =====================================================
   9. INITIALIZE PAGE
===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    function () {


        /* Load live blood data */

        loadBloodAvailability();


        /* Find Blood button */

        const findButton =
            document.getElementById(
                "findBloodBtn"
            );


        if (findButton) {

            findButton.addEventListener(
                "click",
                findBlood
            );

        }


        /* Join Network form */

        const bloodForm =
            document.getElementById(
                "bloodAvailabilityForm"
            );


        if (bloodForm) {

            bloodForm.addEventListener(
                "submit",
                submitBloodAvailability
            );

        }

    }
);

</script>