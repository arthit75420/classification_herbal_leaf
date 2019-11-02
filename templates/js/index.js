/**
 * . => class
 * # => id
 */
var cropper;

/**
 * Cookie
 */

class Cookie {
    constructor(init) {
        this.init = init;
    }
    setCookie(cname, cvalue, exdays) {
        let d = new Date();
        d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
        let expires = "expires=" + d.toUTCString();
        document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
        return true;
    }
    getCookie(cname) {
        let name = cname + "=";
        let ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) == ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) == 0) {
                return c.substring(name.length, c.length);
            }
        }
        return "";
    }
    checkCookie(cname) {
        return this.getCookie(cname) != "";
    }
}

/**
 * Dom Event
 */
/* Crypto random is safty don't use Math.random */
const crypto = window.crypto || window.msCrypto;
var IDarray = new Uint32Array(1);
window.addEventListener('DOMContentLoaded', () => {
    let cookie = new Cookie();
    if (!cookie.checkCookie("id")) cookie.setCookie("id", (+`0.${crypto.getRandomValues(IDarray)}`).toString(36).substr(2,10), 1);
    sessionStorage.setItem("TopOne", "leaf");
    let $selectLeaf = $("#leafs");
    let $alert = $('#results-predict');
    let $boxSaveImg = $('#box-save-img');
    $alert.hide();
    $("#accurate").click(() => {
        $selectLeaf.empty();
        try {
            let leafs = JSON.parse(sessionStorage.getItem("leafs"));
            let topOneLeaf = sessionStorage.getItem("TopOne");
            $.each(leafs, (idx, obj) => {
                if (obj.leaf == topOneLeaf) {
                    $selectLeaf.append(`<option value="${obj.leaf}">${obj.leafThai}</option>`);
                    return false;
                }
            });
            $selectLeaf.prop('disabled', true);
        } catch (e) {}
    });

    $("#inaccurate").click(() => {
        $selectLeaf.empty();
        try {
            let leafs = JSON.parse(sessionStorage.getItem("leafs"));
            $selectLeaf.prop('disabled', false);
            $selectLeaf.append(`<option value="0" selected hidden>กรุณาเลือกใบ</option>`);
            $.each(leafs, (idx, obj) => {
                $selectLeaf.append(`<option value="${obj.leaf}">${obj.leafThai}</option>`);
            });
        } catch (e) {}
    });
    let $btLeafSave = $("#leaf-save");
    $btLeafSave.click(() => {
        let leaf = $("#leafs").val();
        let id = cookie.getCookie("id");
        if ($("#leafs").val() != "0") {
            $.ajax({
                url: "save",
                method: "POST",
                dataType: "json",
                data: {
                    leaf,
                    id
                }
            }).done((res) => {
                if (res.status == "success") {
                    Swal.fire({
                        type: 'success',
                        title: 'บันทึกภาพเรียบร้อยแล้ว',
                        showConfirmButton: false,
                        timer: 1500
                    });
                    $boxSaveImg.empty().html(`<div class="alert alert-success">
                                                    <strong>บันทึกภาพเรียบร้อยแล้ว!</strong>
                                                    </div>`);
                } else if (res.status == "error") {
                    Swal.fire({
                        type: 'error',
                        title: res.response,
                        showConfirmButton: false,
                        timer: 1500
                    });
                } else {
                    Swal.fire({
                        type: 'error',
                        title: 'System error!',
                        showConfirmButton: false,
                        timer: 1500
                    });
                }

            }).fail((res) => {
                Swal.fire({
                    type: 'error',
                    title: 'บันทึกภาพล้มเหลว',
                    showConfirmButton: false,
                    timer: 1500
                });
            });
        } else {
            $("#leafs").focus();
        }
    });
    // $("#select-leaf").on('hide.bs.modal', () => {
    //     $btLeafSave.removeAttr("data-dismiss");
    // });
    $("#select-leaf").on('show.bs.modal', () => {
        if ($("#leafs").val() != "0") $btLeafSave.attr("data-dismiss", "modal");
        else $btLeafSave.removeAttr("data-dismiss");
    });

    $("#leafs").change(() => {
        if ($("#leafs").val() != "0") $btLeafSave.attr("data-dismiss", "modal");
    });

    var avatar = document.getElementById('avatar');
    var image = document.getElementById('image');
    var input = document.getElementById('input');
    var predict = document.getElementById('predict');
    var $results = $("#results");
    var $progress = $('.progress');
    var $progressBar = $('.progress-bar');

    var $modal = $('#modal');
    $('[data-toggle="tooltip"]').tooltip();

    input.addEventListener('change', (e) => {
        var files = e.target.files;
        var done = (imgUrl) => {
            input.value = '';
            image.src = imgUrl;
            $alert.hide();
            $modal.modal('show');
        };
        var reader;
        var file;

        if (files && files.length > 0) {
            file = files[0];

            if (URL) {
                done(URL.createObjectURL(file));
            } else if (FileReader) {
                reader = new FileReader();
                reader.onload = () => {
                    done(reader.result);
                };
                reader.readAsDataURL(file);
            }
        }
    });

    predict.addEventListener('click', () => {
        $(predict).hide();
        $progressBar.width('0%').attr('aria-valuenow', '0').text('0%');
        $progress.show();
        $alert.removeClass('alert-success alert-warning');
        canvas.toBlob((blob) => {
            let id = cookie.getCookie("id");
            var formData = new FormData();
            formData.append('file', blob, 'leaf.png');
            formData.append("id", id);
            $.ajax({
                url: "predict",
                method: "POST",
                dataType: "json",
                data: formData,
                processData: false,
                contentType: false,
                xhr: () => {
                    var xhr = new XMLHttpRequest();

                    xhr.upload.onprogress = (e) => {
                        if (e.lengthComputable) {
                            let percent = Math.round((e.loaded / e.total) * 100);
                            $progressBar.width(percentage).attr('aria-valuenow', percent).text(`${percent}%`);
                        }
                    };
                    return xhr;
                }
            }).done((res) => {
                if (res.status == "success") {
                    $results.empty();
                    if (sessionStorage.getItem("leafs") == null)
                        sessionStorage.setItem("leafs", JSON.stringify(res.response.leafs));
                    $.each(res.response.results, (_i, result) => {
                        if (_i == 0) sessionStorage.setItem("TopOne", result.leaf);
                        $results.append(`<tr>
                                            <td>${result.leafThai}</td>
                                            <td>${result.percent}%</td>
                                            <td>${result.perfect}</td>
                                        </tr>`);
                    });
                    $("#results-box").removeClass('d-none');
                    $alert.show().addClass('alert-success');
                } else if (res.status == "error") {
                    $("#results-box").addClass('d-none');
                    $alert.show().addClass('alert-warning').text(res.response);
                } else {
                    $("#results-box").addClass('d-none');
                    $alert.show().addClass('alert-danger').text("System error!");
                }
            }).fail(() => {
                avatar.src = initialAvatarURL;
                $("#results-box").addClass('d-none');
                $alert.show().addClass('alert-warning').text('Upload error');
            }).always(() => {
                $progress.hide();
            });
        });
    });

    $modal.on('shown.bs.modal', () => {
        cropper = new Cropper(image, {
            dragMode: 'move',
            aspectRatio: 3 / 4,
            autoCropArea: 0.85,
            restore: false,
            guides: false,
            center: false,
            highlight: false,
            cropBoxMovable: false,
            cropBoxResizable: false,
            toggleDragModeOnDblclick: false,
            rotatable: true
        });
    }).on('hidden.bs.modal', () => {
        cropper.destroy();
        cropper = null;
    });
    var initialAvatarURL;
    var canvas;
    document.getElementById('crop').addEventListener('click', () => {
        if (cropper) {
            $(predict).show();
            canvas = cropper.getCroppedCanvas({
                width: 768,
                height: 1024,
            });
            initialAvatarURL = avatar.src;
            avatar.src = canvas.toDataURL();
            $("#leafShow").attr("src", canvas.toDataURL());
            $boxSaveImg.empty().html(`<button type="button" class="btn btn-primary" 
                                        data-toggle="modal" data-target="#report" 
                                        id="bt-save">บันทึกภาพ</button>`);
        }
    });
});