define(['jquery', 'base/js/namespace', 'base/js/dialog', 'base/js/utils'], function($, jupyter, dialog, utils) {
  'use strict';

  let message = `Connect to an existing kernel launched outside of the notebook.<br/><br/>
If the kernel you want to connect to was the last kernel launched you don't need to enter 
anything for the connection file, otherwise enter either the full path to the 
connection file or just the base name if you started the kernel in the usual way.
If the kernel isn't running on localhost please provide the server's name but note that 
tunneling requires passwordless ssh for now.`;

  function open_nb(conn_file, server="", port="", transport="") {
    var url = utils.url_path_join(utils.get_body_data('baseUrl'), 'existing');

    var params = [];
    if (conn_file != "") { params.push("conn_file=" + conn_file); }
    if (server != "") { params.push("server=" + server); }
    if (port != "") { params.push("port=" + port); }
    if (transport != "") { params.push("transport=" + transport); }
    if (params.length > 0) { url += "?" + params.join("&"); }

    // we do post so that errors pop up in an error box
    var settings = { type: 'POST' };

    var w = window.open('', '_blank');
    w.document.write('<p>trying to connect, please wait...<p/>');

    utils.promising_ajax(url, settings).then(function(data) {
      console.log(data);
      w.location = data.path;
    }).catch(function(e) {
      w.close()
      dialog.modal({
        title: 'Unable to connect to existing kernel',
        body: $('<div/>').addClass('alert alert-danger').text(e.message || e),
        buttons: { Ok: {'class': 'btn-primary'} }
      });
    });
  }

  function row(label, id, placeholder, size=40) {
    return $('<tr/>')
      .append($('<td/>')
        .css('text-align', 'right')
        .css('padding', '5px')
        .append($('<label/>')
          .text(label)))
      .append($('<td/>')
        .css('padding', '5px')
        .append($('<input/>')
          .attr('type', 'text')
          .attr('size', size)
          .attr('placeholder', placeholder)
          .attr('id', id)));
  }

  function show_modal() {
    var radio = $('<tr/>')
      .append($('<td/>')
        .css('text-align', 'right')
        .css('padding', '5px')
        .append($('<label/>')
          .text("Protocol")))
      .append($('<td/>')
        .css('padding', '5px')
        .append($('<input/>')
          .attr('type', 'radio')
          .attr('name', 'transport-radio')
          .attr('value', 'ipc')
          .attr('checked', 'checked'))
        .append($('<label/>')
          .css('padding-right', '10px')
          .css('padding-left', '5px')
          .text("ipc"))
        .append($('<input/>')
          .attr('type', 'radio')
          .attr('name', 'transport-radio')
          .attr('value', 'tcp')
          .html('tcp'))
        .append($('<label/>')
          .css('padding-left', '5px')
          .text("tcp")));

    var body = $('<div/>')
      .append($('<div/>')
        .html(message))
      .append($('<br/>'))
      .append($('<table/>')
        .append(row('Connection file', 'connection-file-text',
            '<most recent kernel-abc.json>'))
        .append(row('Server', 'server-name-text', 'localhost'))
        .append(row('Port', 'port-number-text', '22'))
        .append(radio));

    dialog.modal({
      title: "Connect to an existing kernel",
      buttons: {
        Connect: {
          class: 'btn-primary', click: function() {
            open_nb($('#connection-file-text').val(),
              $('#server-name-text').val(),
              $('#port-number-text').val(),
              $('input[name="transport-radio"]:checked').val()
            );
          }
        }
      },
      body: body
    });
  }

  // insert the "Existing" button to the right of the "New" button
  function load_extension() {
    var space = $('<span/>').text(' ').insertAfter('#new-buttons');

    $('<button/>')
      .attr('type', 'button')
      .attr('id', 'connect_to_existing')
      .attr('title', 'Connect Existing')
      .attr('aria-label', 'connect to an existing kernel')
      .addClass('btn btn-default btn-xs')
      .text('Existing')
      .on('click', function(e) { show_modal(); })
      .appendTo(space);
  }

  return {
    load_ipython_extension : load_extension
  };
});
