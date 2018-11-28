define(['jquery', 'base/js/namespace', 'base/js/dialog', 'base/js/utils'], function($, jupyter, dialog, utils) {
  'use strict';

  let message = `Connect to an existing kernel launched outside of the notebook.<br/>
<br/>
You can either enter the full path to the connection file or just the base name if you started the kernel in the usual way.`;

  function open_nb(conn_file) {
    var url = utils.url_path_join(utils.get_body_data('baseUrl'), 'existing', conn_file);
    var w = window.open('', '_blank');
    w.document.write('<p>trying to connect, please wait...<p/>');
    
    utils.promising_ajax(url, {type: "POST"}).then(function(data) {
      console.log(data);
      w.location = utils.url_path_join(utils.get_body_data('baseUrl'), 'notebooks', data.notebook.path);
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
    var body = $('<div/>');

    $('<div/>')
      .html(message)
      .appendTo(body);

    $('<br/>').appendTo(body);

    $('<table/>')
      .append(row('Connection file:', 'connection-file', 'kernal-abc.json'))
      .appendTo(body);
    // TODO: for kernels not on localhost
    //.append(row('Server', 'server-name'))

    dialog.modal({
      title: "Connect to an existing kernel",
      buttons: {
        Connect: {
          class: 'btn-primary', click: function() { open_nb($('#connection-file').val()); }
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
