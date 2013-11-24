""":mod:`libearth.compat.xmlpullreader` --- Pulling SAX parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import xml.sax.xmlreader

__all__ = 'PullReader',


class PullReader(xml.sax.xmlreader.XMLReader):
    """SAX parser interface which provides similar but slightly less power
    than :class:`~xml.sax.xmlreader.IncremenetalParser`.

    :class:`~xml.sax.xmlreader.IncrementalParser` can feed arbitrary length
    of bytes while it can't determine how long bytes to feed.

    """

    def feed(self):
        """This method makes the parser to parse the next step node,
        emitting the corresponding events.

        :meth:`feed()` may raise :exc:`~xml.sax.SAXException`.

        :returns: whether the stream buffer is not empty yet
        :rtype: :class:`bool`
        :raises xml.sax.SAXException: when something goes wrong

        """
        raise NotImplementedError(
            'every subclass of {0.__module__}.{0.__name__} has to '
            'implement feed() method'.format(PullReader)
        )

    def prepareParser(self, iterable):
        """This method is called by the parse implementation to allow
        the SAX 2.0 driver to prepare itself for parsing.

        :param iterable: iterable of :class:`bytes`
        :type iterable: :class:`collections.Iterable`

        """
        raise NotImplementedError(
            'every subclass of {0.__module__}.{0.__name__} has to '
            'implement prepareParser() method'.format(PullReader)
        )

    def close(self):
        """This method is called when the entire XML document has been
        passed to the parser through the feed method, to notify the
        parser that there are no more data. This allows the parser to
        do the final checks on the document and empty the internal
        data buffer.

        The parser will not be ready to parse another document until
        the reset method has been called.

        :meth:`close()` may raise :exc:`~xml.sax.SAXException`.

        :raises xml.sax.SAXException: when something goes wrong

        """
        raise NotImplementedError(
            'every subclass of {0.__module__}.{0.__name__} has to '
            'implement close() method'.format(PullReader)
        )

    def reset(self):
        """This method is called after close has been called to reset
        the parser so that it is ready to parse new documents.
        The results of calling parse or feed after close without calling
        reset are undefined.

        """
        raise NotImplementedError(
            'every subclass of {0.__module__}.{0.__name__} has to '
            'implement reset() method'.format(PullReader)
        )
