
document.addEventListener("DOMContentLoaded", function () {
    initializeCalendarSelection();

    // =====================================
    // 1. LOAD REPORT DATA
    // =====================================

    const reportDataElement = document.getElementById("reportChartData");

    if (!reportDataElement) {
        console.error("Report chart data was not found.");
        return;
    }

    let reportData;

    try {
        reportData = JSON.parse(reportDataElement.textContent);
    } catch (error) {
        console.error("Unable to read report chart data:", error);
        return;
    }

    // Check if Chart.js is available.
    if (typeof Chart === "undefined") {
        console.error("Chart.js library could not be loaded.");
        return;
    }

    reportData.stats = reportData.stats || {};
    reportData.weekly = reportData.weekly || { labels: [], values: [] };
    reportData.monthly = reportData.monthly || { labels: [], values: [] };
    reportData.weekly.labels = reportData.weekly.labels || [];
    reportData.weekly.values = reportData.weekly.values || [];
    reportData.monthly.labels = reportData.monthly.labels || [];
    reportData.monthly.values = reportData.monthly.values || [];


    // =====================================
    // 2. GLOBAL CHART SETTINGS
    // =====================================

    Chart.defaults.color = "#94A3B8";
    Chart.defaults.font.family = "Arial, sans-serif";

    const gridColor = "rgba(148, 163, 184, 0.12)";

    const chartColors = {
        blue: "#3B82F6",
        lightBlue: "#60A5FA",
        yellow: "#F59E0B",
        gray: "#64748B",
        white: "#F8FAFC"
    };


    // =====================================
    // 3. DOUGHNUT CHART CENTER TOTAL
    // =====================================

    const centerTextPlugin = {
        id: "centerText",

        afterDraw(chart) {

            if (chart.config.type !== "doughnut") {
                return;
            }

            const { ctx, chartArea } = chart;

            if (!chartArea) {
                return;
            }

            const total = chart.data.datasets[0].data.reduce(
                (sum, value) => sum + Number(value || 0),
                0
            );

            const centerX = (chartArea.left + chartArea.right) / 2;
            const centerY = (chartArea.top + chartArea.bottom) / 2;

            ctx.save();

            ctx.textAlign = "center";
            ctx.textBaseline = "middle";

            // Total number.
            ctx.font = "bold 30px Arial";
            ctx.fillStyle = chart.$printing ? "#334155" : chartColors.white;

            ctx.fillText(
                total,
                centerX,
                centerY - 8
            );

            // Center label.
            ctx.font = "11px Arial";
            ctx.fillStyle = chart.$printing ? "#475569" : "#94A3B8";

            ctx.fillText(
                "TOTAL ACTIVITIES",
                centerX,
                centerY + 18
            );

            ctx.restore();
        }
    };


    // =====================================
    // 4. TASK STATUS DOUGHNUT CHART
    // =====================================

    const statusCanvas = document.getElementById("statusChart");

    if (statusCanvas && !Chart.getChart(statusCanvas)) {

        const statusValues = [
            Number(reportData.stats.completed || 0),
            Number(reportData.stats.in_progress || 0),
            Number(reportData.stats.pending || 0)
        ];

        new Chart(statusCanvas, {

            type: "doughnut",

            plugins: [centerTextPlugin],

            data: {

                labels: [
                    "Completed",
                    "In Progress",
                    "Pending"
                ],

                datasets: [{

                    data: statusValues,

                    backgroundColor: [
                        chartColors.blue,
                        chartColors.yellow,
                        chartColors.gray
                    ],

                    hoverBackgroundColor: [
                        chartColors.lightBlue,
                        "#FBBF24",
                        "#94A3B8"
                    ],

                    borderColor: "#111827",
                    borderWidth: 4,
                    hoverOffset: 8
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                cutout: "65%",

                plugins: {

                    legend: {
                        position: "bottom",

                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: "circle"
                        }
                    },

                    tooltip: {

                        callbacks: {

                            label: function (context) {

                                const value = Number(context.raw || 0);

                                const total = context.dataset.data.reduce(
                                    (sum, item) => sum + Number(item || 0),
                                    0
                                );

                                const percentage = total > 0
                                    ? ((value / total) * 100).toFixed(1)
                                    : "0.0";

                                return ` ${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }


    // =====================================
    // 5. WEEKLY ACTIVITY BAR CHART
    // =====================================

    const weeklyCanvas = document.getElementById("weeklyActivityChart");

    if (weeklyCanvas && !Chart.getChart(weeklyCanvas)) {

        new Chart(weeklyCanvas, {

            type: "bar",

            data: {

                labels: reportData.weekly.labels,

                datasets: [{

                    label: "Activities",

                    data: reportData.weekly.values,

                    backgroundColor: chartColors.blue,
                    hoverBackgroundColor: chartColors.lightBlue,

                    borderRadius: 6,
                    maxBarThickness: 45
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                plugins: {

                    legend: {
                        display: false
                    },

                    tooltip: {

                        callbacks: {

                            label: function (context) {

                                const value = Number(context.raw || 0);

                                return ` ${value} ${value === 1 ? "activity" : "activities"}`;
                            }
                        }
                    }
                },

                scales: {

                    x: {

                        grid: {
                            display: false
                        }
                    },

                    y: {

                        beginAtZero: true,

                        ticks: {
                            precision: 0,
                            stepSize: 1
                        },

                        grid: {
                            color: gridColor
                        }
                    }
                }
            }
        });
    }


    // =====================================
    // 6. MONTHLY ACTIVITY BAR CHART
    // =====================================

    const monthlyCanvas = document.getElementById("monthlyActivityChart");

    if (monthlyCanvas && !Chart.getChart(monthlyCanvas)) {

        new Chart(monthlyCanvas, {

            type: "bar",

            data: {

                labels: reportData.monthly.labels.map(
                    date => Number(date.split("-")[2])
                ),

                datasets: [{

                    label: "Activities",

                    data: reportData.monthly.values,

                    backgroundColor: chartColors.blue,
                    hoverBackgroundColor: chartColors.lightBlue,

                    borderRadius: 4,
                    maxBarThickness: 24
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                plugins: {

                    legend: {
                        display: false
                    },

                    tooltip: {

                        callbacks: {

                            title: function (items) {

                                return `Day ${items[0].label}`;
                            },

                            label: function (context) {

                                const value = Number(context.raw || 0);

                                return ` ${value} ${value === 1 ? "activity" : "activities"}`;
                            }
                        }
                    }
                },

                scales: {

                    x: {

                        title: {
                            display: true,
                            text: "Day of the Month"
                        },

                        grid: {
                            display: false
                        }
                    },

                    y: {

                        beginAtZero: true,

                        ticks: {
                            precision: 0,
                            stepSize: 1
                        },

                        grid: {
                            color: gridColor
                        }
                    }
                }
            }
        });
    }

    const reportCanvases = [
        statusCanvas,
        weeklyCanvas,
        monthlyCanvas
    ].filter(Boolean);

    window.addEventListener("beforeprint", function () {
        Chart.defaults.color = "#334155";

        reportCanvases.forEach(function (canvas) {
            const chart = Chart.getChart(canvas);

            if (!chart) {
                return;
            }

            chart.$printing = true;

            if (chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = "#334155";
            }

            if (chart.options.scales) {
                Object.values(chart.options.scales).forEach(function (scale) {
                    scale.ticks.color = "#334155";
                    if (scale.title) {
                        scale.title.color = "#334155";
                    }
                });
            }

            chart.resize();
            chart.update("none");
        });
    });

    window.addEventListener("afterprint", function () {
        Chart.defaults.color = "#94A3B8";

        reportCanvases.forEach(function (canvas) {
            const chart = Chart.getChart(canvas);

            if (!chart) {
                return;
            }

            chart.$printing = false;

            if (chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = "#94A3B8";
            }

            if (chart.options.scales) {
                Object.values(chart.options.scales).forEach(function (scale) {
                    scale.ticks.color = "#94A3B8";
                    if (scale.title) {
                        scale.title.color = "#94A3B8";
                    }
                });
            }

            chart.resize();
            chart.update("none");
        });
    });

    document.querySelectorAll("[data-print-report]").forEach(function (button) {
        button.addEventListener("click", function () {
            window.print();
        });
    });
});

function initializeCalendarSelection() {
    const calendarButtons = document.querySelectorAll("[data-calendar-date]");
    const clearCalendarSelection = document.getElementById("clear-calendar-selection");
    const activityHeading = document.getElementById("monthly-activity-heading");
    const activityTable = document.getElementById("monthly-activity-table");
    const emptyActivities = document.getElementById("monthly-activity-empty");
    const activityRows = activityTable
        ? Array.from(activityTable.querySelectorAll("[data-activity-date]"))
        : [];
    const defaultActivityHeading = activityHeading
        ? activityHeading.textContent
        : "";

    function selectCalendarDate(selectedDate) {
        let visibleRows = 0;

        calendarButtons.forEach(function (button) {
            const isSelected = button.dataset.calendarDate === selectedDate;
            button.setAttribute("aria-pressed", String(isSelected));
        });

        activityRows.forEach(function (row) {
            const isVisible = !selectedDate
                || row.dataset.activityDate === selectedDate;
            row.hidden = !isVisible;
            if (isVisible) {
                visibleRows += 1;
            }
        });

        if (activityTable) {
            activityTable.hidden = visibleRows === 0;
        }

        if (emptyActivities) {
            emptyActivities.hidden = visibleRows > 0;
            if (selectedDate) {
                emptyActivities.querySelector("h3").textContent =
                    "No matching activities on this date.";
                emptyActivities.querySelector("p").textContent =
                    `No activities match the selected date and filters (${selectedDate}).`;
            } else {
                emptyActivities.querySelector("h3").textContent =
                    "No matching activities for this month.";
                emptyActivities.querySelector("p").textContent =
                    "Try changing or clearing the report filters.";
            }
        }

        if (activityHeading) {
            activityHeading.textContent = selectedDate
                ? `${visibleRows} matching ${visibleRows === 1 ? "activity" : "activities"} on ${selectedDate}.`
                : defaultActivityHeading;
        }

        if (clearCalendarSelection) {
            clearCalendarSelection.hidden = !selectedDate;
        }
    }

    calendarButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const selectedDate = button.getAttribute("aria-pressed") === "true"
                ? ""
                : button.dataset.calendarDate;
            selectCalendarDate(selectedDate);
        });
    });

    if (clearCalendarSelection) {
        clearCalendarSelection.addEventListener("click", function () {
            selectCalendarDate("");
        });
    }
}
