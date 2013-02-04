from musik.db import IdentifierGenerator

class TestIdentifierGenerator(object):
    # Default ID length
    id_length = 4
    def setUp(self):
        self.generator = IdentifierGenerator()
        pass

    def test_lengths(self):
        for x in range(3):
            generator = IdentifierGenerator(x+5)
            yield self.check_length, generator.next(), x + 5 
            pass
        pass
    
    def check_length(self, id_generated, length):
        assert type(id_generated) == str
        assert len(id_generated) == length
        pass
        
    def test_next(self):
        generated = self.generator.next()
        self.check_length(generated, length=self.id_length)
        pass 
    pass
